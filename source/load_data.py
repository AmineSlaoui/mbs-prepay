# Reads data directly from data/fannie/Performance_All.zip (too large to unzip)
"""Loan-level sampler for Fannie Mae `Performance_All.zip`.

The zip holds one pipe-delimited, header-less CSV per acquisition quarter
(2000Q1 ... 2026Q1, ~950 GB uncompressed). Layout follows
`references/crt-file-layout-and-glossary.pdf` ("Single-Family Loan Performance
Dataset and CRT - Glossary and File Layout"): rows have 113 fields, i.e. field
positions 1-113 of the PDF. Field 114 (Origination VantageScore 4.0) is only
populated from the May 2026 activity period and is not in this extract.

Rows inside each file are sorted by Loan Identifier, then reporting period, and
loan IDs are scrambled, so the first N bytes of a file are a random sample of
complete loan histories. `read_performance_sample` exploits that: it streams
only the head of each member and drops the last (possibly truncated) loan.
"""

import io
import zipfile
from pathlib import Path

import polars as pl
from tqdm.auto import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERFORMANCE_ZIP = PROJECT_ROOT / "data" / "fannie" / "Performance_All.zip"

N_FIELDS = 113

# 1-based field position (as in the PDF layout) -> column name
FIELDS = {
    2: "loan_id",
    3: "rep_period",  # MMYYYY
    4: "channel",  # R retail / C correspondent / B broker
    8: "orig_rate",
    10: "orig_upb",
    12: "cur_upb",  # masked as 0.00 during the first 6 months of loan life
    13: "orig_term",
    14: "orig_date",  # MMYYYY
    15: "first_pay_date",  # MMYYYY
    16: "loan_age",
    20: "ltv",
    21: "cltv",
    22: "num_borrowers",
    23: "dti",
    24: "fico",  # borrower credit score at origination
    25: "co_fico",
    26: "first_time_buyer",
    27: "loan_purpose",  # P purchase / C cash-out refi / R rate-term refi
    28: "property_type",
    29: "num_units",
    30: "occupancy",  # P primary / S second / I investor
    31: "state",
    35: "amort_type",
    40: "dlq_status",
    44: "zero_bal_code",  # 01 = prepaid or matured
    45: "zero_bal_date",
    46: "upb_at_removal",
    111: "fico_classic_orig",  # populated from Dec 2025 activity; backfills field 24
}

FLOAT_COLS = ["orig_rate", "orig_upb", "cur_upb", "upb_at_removal"]
INT_COLS = ["orig_term", "loan_age", "ltv", "cltv", "num_borrowers", "dti",
            "fico", "co_fico", "num_units", "fico_classic_orig"]


def list_members(zip_path=PERFORMANCE_ZIP):
    """Quarterly CSV names in chronological order."""
    with zipfile.ZipFile(zip_path) as zf:
        return sorted(n for n in zf.namelist() if n.endswith(".csv"))


def _read_head(zf, member, n_bytes):
    with zf.open(member) as fh:
        raw = fh.read(n_bytes)
        complete = len(raw) < n_bytes  # whole member fit in the budget
    if not complete:
        raw = raw[: raw.rfind(b"\n") + 1]
    n_fields = raw[: raw.find(b"\n")].count(b"|") + 1
    if n_fields != N_FIELDS:
        raise ValueError(f"{member}: {n_fields} fields per row, layout expects {N_FIELDS}")
    df = pl.read_csv(
        io.BytesIO(raw),
        separator="|",
        has_header=False,
        columns=[f"column_{p - 1}" for p in FIELDS],  # polars names columns from 0
        infer_schema=False,  # everything as Utf8; typed in `_cast`
        quote_char=None,
    )
    if df.width != len(FIELDS):
        raise ValueError(f"{member}: expected {len(FIELDS)} selected columns, got {df.width}")
    df = df.rename({f"column_{p - 1}": name for p, name in FIELDS.items()})
    if not complete:
        df = df.filter(pl.col("loan_id") != df["loan_id"][-1])
    return df


def _cast(df):
    return df.with_columns(
        [pl.col(c).cast(pl.Float64, strict=False) for c in FLOAT_COLS]
        + [pl.col(c).cast(pl.Int32, strict=False) for c in INT_COLS]
        + [pl.col(c).cast(pl.Categorical) for c in
           ["channel", "first_time_buyer", "loan_purpose", "property_type",
            "occupancy", "state", "amort_type", "dlq_status", "zero_bal_code"]]
    )


def read_performance_sample(mb_per_file=80, members=None, zip_path=PERFORMANCE_ZIP):
    """Sample complete loan histories from the head of every quarterly file.

    Returns one row per loan-month with the columns in `FIELDS` plus
    `acq_quarter` (source file).
    """
    members = members or list_members(zip_path)
    frames = []
    with zipfile.ZipFile(zip_path) as zf:
        for m in tqdm(members, desc="quarters"):
            df = _read_head(zf, m, int(mb_per_file * 1e6))
            frames.append(_cast(df).with_columns(acq_quarter=pl.lit(m[:-4])))
    return pl.concat(frames)


def load_performance_sample(cache_path, mb_per_file=80, refresh=False):
    """`read_performance_sample` with a parquet cache."""
    cache_path = Path(cache_path)
    if cache_path.exists() and not refresh:
        return pl.read_parquet(cache_path)
    df = read_performance_sample(mb_per_file=mb_per_file)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(cache_path)
    return df
