"""New York Times articles about mortgages, from the NYT Archive API (one request returns every article of a month).

`download()` saves one small JSON per month in data/nyt/: the month's total article count plus the articles whose
headline, abstract or lead paragraph matches MORTGAGE. Months already saved are skipped, so it can be stopped and
rerun. Needs NYT_API_KEY in .env (developer.nytimes.com, Archive API enabled). `load()` reads them back.
"""
import json
import os
import re
import time
from datetime import date
from pathlib import Path

import polars as pl
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "nyt"
URL = "https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"
MORTGAGE = re.compile(r"mortgage|refinanc|home loan", re.I)  # broad on purpose; notebooks narrow it down
WAIT = 12  # seconds between requests: the API allows 5 per minute


def _text(doc):
    return " ".join([(doc.get("headline") or {}).get("main") or "", doc.get("abstract") or "",
                     doc.get("lead_paragraph") or ""])


def _fetch(year, month, key):
    for attempt in range(5):
        r = requests.get(URL.format(year=year, month=month), params={"api-key": key}, timeout=300)
        if r.status_code == 429:  # rate limited: wait and retry
            time.sleep(60 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["response"]["docs"]
    raise RuntimeError(f"NYT archive {year}-{month:02d}: still rate limited after 5 tries")


def download(start=(1999, 1), end=None):
    """Save months start..end (inclusive, (year, month)); end defaults to last month."""
    load_dotenv(ROOT / ".env")
    key = os.environ["NYT_API_KEY"]
    today = date.today()
    end = end or ((today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12))
    OUT.mkdir(parents=True, exist_ok=True)
    y, m = start
    while (y, m) <= end:
        path = OUT / f"{y}-{m:02d}.json"
        if not path.exists():
            docs = _fetch(y, m, key)
            keep = [{"pub_date": d.get("pub_date"), "headline": (d.get("headline") or {}).get("main"),
                     "abstract": d.get("abstract"), "lead_paragraph": d.get("lead_paragraph"),
                     "section": d.get("section_name"), "type": d.get("type_of_material")}
                    for d in docs if MORTGAGE.search(_text(d))]
            tmp = path.with_suffix(".tmp")  # write then rename, so a stopped run never leaves half a file
            tmp.write_text(json.dumps({"total": len(docs), "articles": keep}))
            tmp.rename(path)
            print(f"{y}-{m:02d}: {len(docs)} articles, {len(keep)} kept", flush=True)
            time.sleep(WAIT)
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)


def load():
    """(articles, totals): saved articles with t (year * 12 + month - 1, as in the model table), and articles per month."""
    articles, totals = [], []
    for path in sorted(OUT.glob("*.json")):
        y, m = map(int, path.stem.split("-"))
        month = json.loads(path.read_text())
        totals.append({"t": y * 12 + m - 1, "total": month["total"]})
        articles += [{"t": y * 12 + m - 1, **a} for a in month["articles"]]
    schema = {"t": pl.Int32, "pub_date": pl.String, "headline": pl.String, "abstract": pl.String,
              "lead_paragraph": pl.String, "section": pl.String, "type": pl.String}
    return pl.DataFrame(articles, schema=schema), pl.DataFrame(totals, schema={"t": pl.Int32, "total": pl.Int64})
