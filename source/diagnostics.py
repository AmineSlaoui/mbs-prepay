"""Standard model check: predicted vs. actual CPR by refi incentive and loan age, plus a SHAP summary.

Run it after every model change, with the old and new model side by side, to see what the change improved.
"""
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

COLORS = ["#2a78d6", "#d6602a", "#2aa876", "#8a2ad6"]  # one per model; actual is black


def cpr(smm):
    return 100 * (1 - (1 - smm) ** 12)


def cpr_by(frame, by, preds, min_rows=2_000):
    """Balance-weighted actual and predicted CPR per value of `by`. `preds` maps model name -> payoff probabilities."""
    cols = ["actual", *preds]
    return (frame.with_columns(pl.col("prepay").alias("actual"), *[pl.Series(n, p) for n, p in preds.items()])
                 .group_by(by)
                 .agg(*[(pl.col(c) * pl.col("exposure")).sum() / pl.col("exposure").sum() for c in cols],
                      balance=pl.col("exposure").sum(), n=pl.len())
                 .filter(pl.col("n") >= min_rows)
                 .with_columns(cpr(pl.col(c)).alias(c) for c in cols)
                 .sort(by))


def plot_over_time(frame, preds):
    """Monthly actual vs. predicted CPR. `frame` needs t (months since year 0), prepay and exposure."""
    d = cpr_by(frame, "t", preds, min_rows=500).with_columns(date=pl.date(pl.col("t") // 12, pl.col("t") % 12 + 1, 1))
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(d["date"], d["actual"], color="#0b0b0b", lw=1.4, label="Actual")
    for name, color in zip(preds, COLORS):
        ax.plot(d["date"], d[name], color=color, lw=1.4, label=name)
    for start, end, label in [(2019, 2022, "valid"), (2022, 2027, "test")]:
        ax.axvspan(np.datetime64(f"{start}-01-01"), np.datetime64(f"{end}-01-01"), color="#e6e5e0", alpha=0.5, lw=0)
        ax.text(np.datetime64(f"{start}-03-01"), ax.get_ylim()[1] * 0.92, label, color="#52514e")
    ax.set(title="Monthly CPR: actual vs. predicted (shaded: years the model did not train on)", ylabel="CPR (%)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    plt.show()


def check(frame, preds):
    """Plot actual vs. predicted CPR by incentive (pp) and loan age (years), and score each model.

    `frame` needs prepay, exposure, incentive and age. The score is the balance-weighted average miss in CPR points
    across buckets (lower is better), so one number per chart says whether a change helped.
    """
    frame = frame.with_columns(incentive_pp=(pl.col("incentive") * 4).round() / 4,  # 0.25 pp steps
                               age_years=pl.col("age").clip(1, 240) // 12 + 1)
    tables = {col: cpr_by(frame, col, preds) for col in ["incentive_pp", "age_years"]}

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    for ax, (col, d) in zip(axes, tables.items()):
        ax.plot(d[col], d["actual"], marker="o", color="#0b0b0b", label="Actual")
        for name, color in zip(preds, COLORS):
            ax.plot(d[col], d[name], marker="o", color=color, label=name)
        ax.set(title=f"CPR by {col}", xlabel=col, ylabel="CPR (%)", ylim=(0, None))
    axes[0].legend()
    fig.tight_layout()
    plt.show()

    errors = pl.DataFrame([{"model": name, **{f"{col}_error": ((d[name] - d["actual"]).abs() * d["balance"]).sum() / d["balance"].sum()
                                                for col, d in tables.items()}} for name in preds])
    return errors, tables


def shap_summary(model, X, title="SHAP summary", n=200_000, top=12, seed=0):
    """Plot the SHAP summary (one dot per loan-month, colored by feature value) and return each feature's share of
    the mean |SHAP| (its pull on predictions) and which way a higher value pushes."""
    Xs = X.sample(min(n, len(X)), random_state=seed)
    shap = model.predict(Xs, num_iteration=model.best_iteration, pred_contrib=True)[:, :-1]  # last column = base value
    impact = np.abs(shap).mean(axis=0)

    rng = np.random.default_rng(seed)
    dots = rng.choice(len(Xs), min(20_000, len(Xs)), replace=False)
    order = np.argsort(impact)[-top:]  # biggest at the top of the chart
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(order) + 1.2))
    for row, i in enumerate(order):
        f = Xs.columns[i]
        color = (dict(c=Xs[f].iloc[dots].rank(pct=True), cmap="coolwarm", vmin=0, vmax=1) if Xs[f].dtype.kind in "if"
                 else dict(c="#a3a29d"))  # categories in gray
        ax.scatter(shap[dots, i], row + rng.uniform(-0.3, 0.3, len(dots)), s=2, alpha=0.4, rasterized=True, **color)
    ax.set_yticks(range(len(order)), Xs.columns[order])
    ax.axvline(0, color="#52514e", lw=0.8)
    ax.set(title=title, xlabel="SHAP value (push on log-odds of payoff; right = faster)")
    fig.colorbar(plt.cm.ScalarMappable(cmap="coolwarm"), ax=ax, label="feature value (low → high; gray = category)")
    fig.tight_layout()
    plt.show()

    direction = [("higher → faster" if np.corrcoef(Xs[f].fillna(Xs[f].median()), shap[:, i])[0, 1] > 0 else "higher → slower")
                 if Xs[f].dtype.kind in "if" else "" for i, f in enumerate(Xs.columns)]  # numeric features only
    return (pl.DataFrame({"feature": list(Xs.columns), "shap_pct": 100 * impact / impact.sum(), "direction": direction})
              .sort("shap_pct", descending=True))
