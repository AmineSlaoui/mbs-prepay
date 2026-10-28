# Reads data directly from data/freddie/raw/historical_data_YYYY.zip (no unzipping needed)
"""Loan-level sampler for the Freddie Mac Single-Family Loan-Level Dataset.

Each `historical_data_YYYY.zip` holds one stored (uncompressed) zip per
origination quarter, `historical_data_YYYYQn.zip`, which in turn holds two
pipe-delimited, header-less files:

- `orig_YYYYQn.txt`: one row per loan, characteristics at origination (31 fields)
- `perf_YYYYQn.txt`: one row per loan per month, monthly performance (35 fields)

Field order follows `references/freddie_general_user_guide_july_2026.pdf`
(Release 48), which lists attributes "in the order in which they appear in the
files". The same 31/35 layout holds for every vintage from 1999 to 2026.

Both files are sorted by Loan Identifier (then period), and the last 7 digits
of the ID are randomly assigned, so the first N bytes of a performance file are
a random sample of complete loan histories. `read_performance_sample` streams
only that head, drops the last (possibly truncated) loan and joins the matching
origination rows.
"""

import io
import zipfile
from pathlib import Path

import polars as pl
from tqdm.auto import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "freddie" / "raw"

ORIG_FIELDS = [
    "fico",  # Classic FICO at origination
    "first_pay_date",  # YYYYMM
    "first_time_buyer",
    "maturity_date",  # YYYYMM
    "msa",
    "mi_pct",
    "num_units",
    "occupancy",  # P primary / S second / I investor
    "cltv",
    "dti",
    "orig_upb",
    "ltv",
    "orig_rate",
    "channel",  # R retail / B broker / C correspondent / T TPO not specified
    "prepay_penalty",
    "amort_type",
    "state",
    "property_type",
    "zip3",
    "loan_id",
    "loan_purpose",  # P purchase / C cash-out refi / N no cash-out refi / R refi not specified
    "orig_term",
    "num_borrowers",
    "seller",
    "super_conforming",
    "pre_harp_loan_id",
    "special_eligibility",  # H Home Possible / F HFA Advantage / R Refi Possible
    "harp",
    "valuation_method",
    "interest_only",
    "vantage_score",  # VantageScore 4.0 at origination
]

PERF_FIELDS = [
    "loan_id",
    "rep_period",  # YYYYMM
    "cur_upb",
    "dlq_status",  # 00 current, 01 30-59 days, ..., RA REO acquisition, XX n/a
    "loan_age",
    "months_to_maturity",
    "defect_settlement_date",
    "mod_flag",
    "zero_bal_code",  # 01 = prepaid or matured
    "zero_bal_date",
    "cur_rate",
    "non_int_upb",
    "ddlpi",  # due date of last paid installment
    "mi_recoveries",
    "net_sale_proceeds",
    "non_mi_recoveries",
    "total_expenses",
    "legal_costs",
    "maint_costs",
    "taxes_insurance",
    "misc_expenses",
    "actual_loss",
    "cum_mod_cost",
    "step_mod",
    "payment_deferral",
    "eltv",
    "upb_at_removal",
    "dlq_accrued_interest",
    "dlq_disaster",
    "assistance_plan",
    "cur_mod_cost",
    "int_upb",
    "mi_cancelled",
    "servicer",
    "bankruptcy_cramdown",
]

# "Not Available" codes from the user guide, mapped to null
NA_CODES = {
    "fico": "9999",
    "vantage_score": "9999",
    "mi_pct": "999",
    "cltv": "999",
    "ltv": "999",
    "dti": "999",
    "eltv": "999",
    "num_units": "99",
    "num_borrowers": "99",
    "property_type": "99",
    "first_time_buyer": "9",
    "occupancy": "9",
    "channel": "9",
    "loan_purpose": "9",
    "valuation_method": "7",
    "mi_cancelled": "7",
    "dlq_status": "XX",
}

FLOAT_COLS = ["orig_rate", "orig_upb", "cur_upb", "cur_rate", "non_int_upb", "int_upb",
              "upb_at_removal", "mi_recoveries", "net_sale_proceeds", "non_mi_recoveries",
              "total_expenses", "legal_costs", "maint_costs", "taxes_insurance",
              "misc_expenses", "actual_loss", "cum_mod_cost", "cur_mod_cost",
              "dlq_accrued_interest", "bankruptcy_cramdown"]
INT_COLS = ["fico", "vantage_score", "mi_pct", "num_units", "cltv", "dti", "ltv",
            "orig_term", "num_borrowers", "loan_age", "months_to_maturity", "eltv"]
CAT_COLS = ["first_time_buyer", "occupancy", "channel", "prepay_penalty", "amort_type",
            "state", "property_type", "loan_purpose", "super_conforming",
            "special_eligibility", "harp", "valuation_method", "interest_only",
            "dlq_status", "mod_flag", "zero_bal_code", "step_mod", "payment_deferral",
            "dlq_disaster", "assistance_plan", "mi_cancelled"]


def list_quarters(raw_dir=RAW_DIR):
    """Origination quarters available in `raw_dir`, e.g. ["1999Q1", ...].

    Yearly zips that are empty or not valid zips (failed downloads) are skipped
    with a warning.
    """
    quarters = []
    for path in sorted(Path(raw_dir).glob("historical_data_*.zip")):
        if not zipfile.is_zipfile(path):
            print(f"skipping {path.name}: not a valid zip (re-download it)")
            continue
        with zipfile.ZipFile(path) as zf:
            quarters += sorted(n[len("historical_data_"):-4] for n in zf.namelist()
                               if n.endswith(".zip"))
    return quarters


def _open_quarter(quarter, raw_dir=RAW_DIR):
    """Inner zip for one quarter. Inner zips are stored, so this is a cheap seek."""
    outer = zipfile.ZipFile(Path(raw_dir) / f"historical_data_{quarter[:4]}.zip")
    return zipfile.ZipFile(outer.open(f"historical_data_{quarter}.zip"))


def _parse(raw, names, member):
    n_fields = raw[: raw.find(b"\n")].count(b"|") + 1
    if n_fields != len(names):
        raise ValueError(f"{member}: {n_fields} fields per row, layout expects {len(names)}")
    return pl.read_csv(
        io.BytesIO(raw),
        separator="|",
        has_header=False,
        new_columns=names,
        infer_schema=False,  # everything as Utf8; typed in `_cast`
        quote_char=None,
    )


def _cast(df):
    return df.with_columns(
        [pl.when(pl.col(c) == code).then(None).otherwise(pl.col(c)).alias(c)
         for c, code in NA_CODES.items() if c in df.columns]
    ).with_columns(
        [pl.col(c).cast(pl.Float64, strict=False) for c in FLOAT_COLS if c in df.columns]
        + [pl.col(c).cast(pl.Int32, strict=False) for c in INT_COLS if c in df.columns]
        + [pl.col(c).cast(pl.Categorical) for c in CAT_COLS if c in df.columns]
    )


def read_origination(quarter, raw_dir=RAW_DIR):
    """All origination rows for one quarter, one row per loan."""
    with _open_quarter(quarter, raw_dir) as zf, zf.open(f"orig_{quarter}.txt") as fh:
        return _cast(_parse(fh.read(), ORIG_FIELDS, f"orig_{quarter}.txt"))


def _read_perf_head(zf, quarter, n_bytes):
    member = f"perf_{quarter}.txt"
    with zf.open(member) as fh:
        raw = fh.read(n_bytes)
        complete = len(raw) < n_bytes  # whole member fit in the budget
    if not complete:
        raw = raw[: raw.rfind(b"\n") + 1]
    df = _parse(raw, PERF_FIELDS, member)
    if not complete:
        df = df.filter(pl.col("loan_id") != df["loan_id"][-1])
    return df


def read_performance_sample(mb_per_file=80, quarters=None, raw_dir=RAW_DIR):
    """Sample complete loan histories from the head of every quarterly performance file.

    Returns one row per loan-month with the columns in `PERF_FIELDS`, the
    origination columns in `ORIG_FIELDS` joined on `loan_id`, and
    `orig_quarter` (source file).
    """
    quarters = quarters or list_quarters(raw_dir)
    frames = []
    for q in tqdm(quarters, desc="quarters"):
        with _open_quarter(q, raw_dir) as zf:
            perf = _read_perf_head(zf, q, int(mb_per_file * 1e6))
            with zf.open(f"orig_{q}.txt") as fh:
                orig = _parse(fh.read(), ORIG_FIELDS, f"orig_{q}.txt")
        orig = orig.filter(pl.col("loan_id").is_in(perf["loan_id"].unique().implode()))
        df = perf.join(orig, on="loan_id", how="left")
        frames.append(_cast(df).with_columns(orig_quarter=pl.lit(q)))
    return pl.concat(frames, how="diagonal_relaxed")


def load_performance_sample(cache_path, mb_per_file=80, refresh=False):
    """`read_performance_sample` with a parquet cache."""
    cache_path = Path(cache_path)
    if cache_path.exists() and not refresh:
        return pl.read_parquet(cache_path)
    df = read_performance_sample(mb_per_file=mb_per_file)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(cache_path)
    return df
