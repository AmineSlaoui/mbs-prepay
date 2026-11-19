"""Turnover + Refi model from notebook 06: data with FRED series, turnover model, and refinance model trained through
SMM = SMM_turn + SMM_refi.

Split (as in notebook 06): train 2000–2022, validate 2023, test 2024 on.
"""
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from scipy.special import expit
from sklearn.metrics import log_loss, roc_auc_score

from diagnostics import cpr

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "combined" / "model_table.parquet"  # built by notebook 03
FRED = ROOT / "data" / "fred"

NO_REFI = -0.5  # incentive (pp) at or below which a loan has no reason to refinance
LOAN = ["age", "orig_upb", "fico", "ltv", "cltv", "dti", "num_borrowers", "num_units", "month",
        "first_time_buyer", "loan_purpose", "property_type", "occupancy", "channel", "state", "agency"]
HOUSING = ["hpa_12m", "new_home_sales"]
TURN_FEATURES = LOAN + ["lockin"] + HOUSING  # notebook 06 best turnover model
REFI_FEATURES = LOAN + ["incentive"]
PARAMS = dict(objective="binary", learning_rate=0.1, num_leaves=63, min_data_in_leaf=2000,  # notebook 04 settings
              feature_fraction=0.8, bagging_fraction=0.5, bagging_freq=1, verbose=-1)
START = np.log(0.005 / 0.995)  # starting refinance score (logit of 0.5% a month); added back at predict


def fred(series, lag=1):
    """Monthly average of data/fred/<series>.csv (PMMS is weekly), keyed by t shifted `lag` months forward."""
    day = pl.col("observation_date").str.to_date()
    return (pl.read_csv(FRED / f"{series}.csv", infer_schema=False)
              .select(t=(day.dt.year() * 12 + day.dt.month() - 1 + lag).cast(pl.Int32),
                      value=pl.col(series).cast(pl.Float64, strict=False))  # FRED marks gaps with "."
              .group_by("t").agg(pl.col("value").mean()).sort("t"))


def load():
    """Model table with PMMS incentive (lag 1), lock-in, housing series and the notebook 06 split."""
    hpi = fred("CSUSHPINSA")
    hpa = hpi.join(hpi.select(t=pl.col("t") + 12, prev="value"), on="t").select(
        "t", hpa_12m=100 * (pl.col("value") / pl.col("prev") - 1))
    return (pl.read_parquet(TABLE)
              .join(fred("MORTGAGE30US").rename({"value": "pmms"}), on="t", how="left")
              .join(hpa, on="t", how="left")
              .join(fred("HSN1F").rename({"value": "new_home_sales"}), on="t", how="left")
              .with_columns(incentive=pl.col("orig_rate") - pl.col("pmms"))
              .with_columns(lockin=pl.col("incentive").clip(None, NO_REFI),
                            split=pl.when(pl.col("year") <= 2022).then(pl.lit("train"))
                                    .when(pl.col("year") == 2023).then(pl.lit("valid")).otherwise(pl.lit("test"))))


def fit(features, train, valid, params={}, start=None, feval=None):
    """LightGBM with the notebook 04 settings, early-stopped on `valid`. `start`: constant starting score (custom loss only)."""
    def dataset(frame, **kw):
        init = None if start is None else np.full(len(frame), start)
        return lgb.Dataset(frame.select(features).to_pandas(), frame["prepay"].to_numpy(), init_score=init, **kw)
    train_set = dataset(train)
    return lgb.train({**PARAMS, **params}, train_set, num_boost_round=1000, valid_sets=[dataset(valid, reference=train_set)],
                     feval=feval, callbacks=[lgb.early_stopping(50, verbose=False)])


def predict(model, features, frame, **kw):
    return model.predict(frame.select(features).to_pandas(), num_iteration=model.best_iteration, **kw)


def score(name, y, p, w):
    return dict(model=name, log_loss=log_loss(y, p), auc=roc_auc_score(y, p),
                actual_cpr=cpr((y * w).sum() / w.sum()), predicted_cpr=cpr((p * w).sum() / w.sum()))


def sigmoid(x):
    # expit avoids the exp overflow: loans with no refinance chance can be pushed to scores below −700, because the
    # loss is flat there (p ≈ turn) and the hessian is tiny. Their probability is 0 either way.
    return expit(x)


def combined(score, turn):
    return np.clip(turn + sigmoid(score), 1e-15, 1 - 1e-15)  # a sum can pass 1; keep the log loss finite


def two_part_loss(turn):
    """Log loss of p = turn + sigmoid(score) for the refinance score (gradient, Fisher-scoring hessian)."""
    def objective(score, dataset):
        s, p, y = sigmoid(score), combined(score, turn), dataset.get_label()
        ds = s * (1 - s)  # dp/dscore
        return ds * (p - y) / (p * (1 - p)), ds * ds / (p * (1 - p))
    return objective


def combined_log_loss(turn):
    def metric(score, dataset):
        return "log_loss", log_loss(dataset.get_label(), combined(score, turn), labels=[0, 1]), False
    return metric


def fit_turnover(data):
    """Turnover model on loans with no reason to refinance; returns it and `data` with a `turn` column added."""
    no_refi = {s: d.filter(pl.col("incentive") <= NO_REFI) for s, d in data.items()}
    model = fit(TURN_FEATURES, no_refi["train"], no_refi["valid"])
    return model, {s: d.with_columns(turn=predict(model, TURN_FEATURES, d)) for s, d in data.items()}


def fit_refi(features, data):
    """Refinance model through p = turn + p_refi (data needs `turn`). Returns (model, frame -> refinance probability)."""
    model = fit(features, data["train"], data["valid"], start=START,
                params=dict(objective=two_part_loss(data["train"]["turn"].to_numpy()), metric="None"),
                feval=combined_log_loss(data["valid"]["turn"].to_numpy()))
    return model, lambda frame: sigmoid(predict(model, features, frame, raw_score=True) + START)
