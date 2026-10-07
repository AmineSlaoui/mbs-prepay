# MBS Prepayment Modeling

Deep learning models for mortgage-backed securities (MBS) prepayment 


## Project structure

```
.
├── data/              # Raw and processed datasets 
├── notebooks/         # Jupyter notebooks for exploration and experiments
├── source/            # Reusable Python code (data loading, models, training)
├── .env               # Local configuration (paths, seed, API keys)
├── requirements.txt   # Python dependencies
└── README.md
```

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


