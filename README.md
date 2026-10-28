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
│   └── freddie/
│       ├── raw/                  # Single-Family Loan-Level Dataset, historical_data_YYYY.zip, 1999-2026
│       └── processed/            # Cached samples 
├── notebooks/
│   └── 01_1d_2d_analysis.ipynb   # Prepayment speed vs. borrower and loan characteristics (1D and 2D)
├── references/
│   └── crt-file-layout-and-glossary.pdf   # Fannie Mae loan performance file layout
├── reports/
│   ├── data_overview.md          # Inventory of what is in data/
│   └── glossary.md               # Definitions of fields and terms used in the notebooks
├── source/
│   └── load_data.py              # Sampler for data/fannie/Performance_All.zip
├── .env                          # Local configuration (seed, API keys)
├── requirements.txt              # Python dependencies
└── README.md
```

The `data/` folder is not in git. Download the files yourself and put them at the paths shown:

- **Fannie Mae:** `Performance_All.zip` comes from the [Single-Family Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/single-family-credit-risk-transfer/fannie-mae-single-family-loan-performance-data)
- **Freddie Mac:** the `historical_data_YYYY.zip` files come from the [Single-Family Loan-Level Dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)

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


