# MBS Prepayment Modeling

Deep learning models for mortgage-backed securities (MBS) prepayment 


## Project structure

```
.
├── data/
│   ├── fannie/
│   │   ├── Performance_All.zip   # Loan-level performance, 2000Q1-2026Q1 
│   │   ├── pool/                 # PoolTalk monthly pool factor files, 2019-06 to 2026-10, one folder per year
│   │   ├── mbs/                  # Data Dynamics BCPR prepayment speeds by seller/servicer
│   │   └── processed/            # Cached samples, e.g. perf_sample_80mb.parquet 
│   ├── freddie/
│   │   ├── raw/                  # Single-Family Loan-Level Dataset, full_set_standard_historical_data.zip, 1999-2026
│   │   └── processed/            # Cached samples 
│   └── combined/
│       └── model_table.parquet   # Fannie + Freddie loan-month table for the models (built by notebook 03)
├── notebooks/
│   ├── 01_1d_2d_analysis.ipynb   # Prepayment speed vs. borrower and loan characteristics (1D and 2D)
│   ├── 02_fannie_vs_freddie.ipynb # Do Fannie and Freddie loans prepay the same way?
│   ├── 03_model_table.ipynb      # Builds data/combined/model_table.parquet (features, target, time split)
│   └── 04_lightgbm.ipynb         # LightGBM v1: payoff probability -> predicted vs. actual CPR (model saved to data/models/)
├── references/
│   ├── fannie_crt-file-layout-and-glossary.pdf    # Fannie Mae file layout (113 fields)
│   └── freddie_general_user_guide_july_2026.pdf   # Freddie Mac user guide (31 origination + 35 performance fields)
├── reports/
│   ├── data_overview.md          # Inventory of what is in data/
│   └── glossary.md               # Definitions of fields and terms used in the notebooks
├── source/
│   ├── fannie_load_data.py       # Sampler for data/fannie/Performance_All.zip
│   └── freddie_load_data.py      # Sampler for data/freddie/raw/full_set_standard_historical_data.zip
├── .env                          # Local configuration (seed, API keys)
├── requirements.txt              # Python dependencies
└── README.md
```

The `data/` folder is not in git. Download the files yourself and put them at the paths shown:

- **Fannie Mae:** `Performance_All.zip` comes from the [Single-Family Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/single-family-credit-risk-transfer/fannie-mae-single-family-loan-performance-data)
- **Freddie Mac:** `full_set_standard_historical_data.zip` (the full Standard Dataset) comes from the [Single-Family Loan-Level Dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)

## Loan-level data

Both datasets describe each loan in two ways:

| | Origination data | Performance data |
|---|---|---|
| **Granularity** | One row per loan | One row per loan per month |
| **Describes** | The loan and borrower when the loan was made. These values never change. | What happens to the loan each month until it ends |
| **Example fields** | FICO, LTV, DTI, original rate and balance, term, purpose, occupancy, state, channel | Current balance, current rate, loan age, delinquency status, modifications, zero balance code (payoff/default) and date |
| **Used for** | Model features (who the borrower is) | Targets and time-varying features (did the loan prepay this month?) |

The two are joined on the loan ID.

- **Fannie Mae** stores both in a single file: each monthly row in `Performance_All.zip` repeats the loan's origination fields (113 fields per row).
- **Freddie Mac** stores them separately. Each origination quarter has an `orig_YYYYQn.txt` (31 fields) and a `perf_YYYYQn.txt` (35 fields), nested as `full_set_standard_historical_data.zip` → `historical_data_YYYY.zip` → `historical_data_YYYYQn.zip`. `freddie_load_data.read_performance_sample` joins the two for you.

Neither dataset has column names. The loaders name columns using the PDFs in `references/`.

## Setup

Requires [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

1. **Create and activate the environment**

   ```bash
   conda create -n mbs-prepay python=3.11 -y
   conda activate mbs-prepay
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Register the Jupyter kernel**

   ```bash
   python -m ipykernel install --user --name mbs-prepay --display-name "Python (mbs-prepay)"
   ```

4. **Configure `.env`**

   Create a `.env` file in the project root (or edit the existing one):

   ```bash
   RANDOM_SEED=

   FANNIE_MAE_API_KEY= Don't know if we are using it yet
   ```

5. **(VS Code) Select the interpreter**

   `Cmd+Shift+P` → **Python: Select Interpreter** → `mbs-prepay`.

## Running

Activate the environment first:

```bash
conda activate mbs-prepay
```

**Notebooks**

```bash
jupyter lab
```

Open a notebook in `notebooks/` and select the **Python (mbs-prepay)** kernel.


