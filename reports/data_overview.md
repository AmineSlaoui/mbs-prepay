# Preliminary Data Check: What's in `data/`

_2026-10-08 · inventory plus ≤1,000-row samples · `data/` untouched_

## `data/Performance_All.zip`: loan-level
- **Contents:** Fannie Mae single-family loans. There is one row per loan per month, with balance, note rate, loan age, delinquency, payoff/termination code, FICO, LTV, state, seller and servicer.
- **Type of loans:** fixed-rate mortgages (`FRM`) with 15/20/25/30-year terms, mostly 30-year.
- **Coverage:** 105 quarterly CSVs, from 2000Q1 to 2026Q1, with no gaps. They total about 950 GB uncompressed. Each file appears to hold the loans *originated* in that quarter, followed monthly until payoff.
- **Caveat:** the files have **no column names** (113 unnamed, pipe-separated columns) and there is no layout file in the repo. The meaning of each column is **UNVERIFIED** until Fannie's official file layout is added.
- **Caveat:** there is no pool ID, so loans can't be matched to specific MBS pools.

## `data/pool/`: pool-level (PoolTalk monthly factor files)
- **Contents:** one row per Fannie MBS security per month: factor, current UPB, WAC, net rate, loan age, prefix, loan count, seller and servicer. Column names are included.
- **Type of loans:** pools of agency mortgages, mostly fixed-rate pools (prefix `CL` dominates), plus some older ARM pools.
- **Coverage:** monthly from 2019-06 to 2026-10, no gaps. `FNM_MF_202108_2.zip` is a 2-row correction file.
- **Caveat:** the columns change 5 times between 2019 and 2026. Placeholder values are common (`77.777`, `999`, `9999`). There is no CPR column, so prepayment speed must be computed from factor changes.

## `data/mbs/`: Data Dynamics "BCPR"
- **Contents:** prepayment speeds aggregated by **seller or servicer**, not by pool or loan. Each row is one GSE (`FN` = Fannie, `FR` = Freddie) × seller or servicer × month × averaging window (1, 3 or 6 months).
- **Type of loans:** fixed-rate mortgages, 15-year (FRM15) and 30-year (FRM30), 2017 to 2026-09.
- **Meaning of BCPR:** not documented. From the data, it appears to be CPR averaged over the window. **UNVERIFIED.**

## Bottom line
- **Loan-level:** best source for modeling, but needs the official column layout first.
- **Pool-level:** usable for pool CPR, but needs header mapping and placeholder cleanup.
- **BCPR:** only useful as a benchmark or servicer feature.
- **Still missing:** market mortgage rates (for refinancing incentive), a home price index, and the official layouts/glossaries.
