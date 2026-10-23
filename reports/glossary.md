# Glossary: MBS Prepayment Terms

_Definitions of the terms used in `notebooks/02_prepayment_characteristics.ipynb` and the other reports. Examples use a $100k loan where possible._

## Core concepts

- **Mortgage-backed security (MBS):** a bond backed by a pool of mortgages. Investors receive the borrowers' monthly payments (interest and principal).
- **Prepayment:** paying off a loan, or part of it, earlier than scheduled. This usually happens when the borrower **sells the home** or **refinances**.
- **Refinancing ("refi"):** taking out a new loan, usually at a lower rate, and using it to pay off the old one.
- **Why prepayment matters:** when borrowers prepay, MBS investors get their money back early, often just as rates have fallen. This changes the value of the security. Predicting prepayment is the core of MBS pricing, and the goal of this project.

## Prepayment speed

- **SMM (Single Monthly Mortality):** the share of the outstanding balance that prepays **in one month**.
  - `SMM = balance prepaid this month / balance outstanding this month`
- **CPR (Conditional Prepayment Rate):** SMM converted to an **annual** rate. This is the standard way to quote prepayment speed.
  - `CPR = 1 - (1 - SMM)^12`
  - **Example:** a pool of 100 loans × $100k = $10M.
    - CPR 5% → about $500k (about 5 loans) prepays over a year. This is **slow**.
    - CPR 40% → about $4M (about 40 loans) prepays over a year. This is **very fast**, typical of a refinancing wave.
  - **For a single loan:** a CPR of 5% is roughly a 5% chance of paying off this year.
- **Voluntary vs. involuntary prepayment:**
  - *Voluntary* means the borrower chose to pay off (sale or refinance). This is what we measure.
  - *Involuntary* means removal through default, foreclosure, short sale or repurchase. These are excluded from our CPR.
- **Curtailment:** a partial prepayment, such as an extra $5k paid toward principal. It is **not included** in our CPR, because the field is blank in the data.
- **Balance-weighted:** each loan counts in proportion to its balance. A $500k payoff moves CPR five times more than a $100k payoff.

## Borrower and loan characteristics

- **UPB (Unpaid Principal Balance):** the amount still owed on the loan.
  - *Original UPB* is the loan amount at origination (the "loan size" in the notebook).
  - *Current UPB* is today's balance. Fannie Mae hides it for the first 6 months of a loan's life, so we use the original UPB for those months.
- **Note rate:** the interest rate on the loan. For fixed-rate loans it never changes.
- **LTV (Loan-to-Value):** loan amount ÷ home value at origination.

  | Home price | Loan | Down payment | LTV |
  |---|---|---|---|
  | $200k | $100k | $100k | 50% |
  | $125k | $100k | $25k | 80% |
  | $103k | $100k | $3k | 97% |

  - **≤ 80%** is the standard "good" threshold, with no mortgage insurance needed.
  - **High LTV** means little equity. These loans prepay more slowly, especially early on.
- **CLTV (Combined LTV):** like LTV, but it also includes any second loans on the property (e.g. a home equity loan). It is always ≥ LTV.
- **Equity:** home value - loan balance. A borrower with **negative equity** ("underwater") owes more than the home is worth and usually can't refinance or sell easily.
- **FICO:** the borrower's credit score (300 to 850). Higher means a better credit history.
  - Below 620 is subprime territory. 740 and above is very good. 800 and above is excellent.
  - High-FICO borrowers refinance much more readily when rates fall.
- **DTI (Debt-to-Income):** monthly debt payments ÷ monthly gross income.
  - Example: $2,000 of debt payments on $5,000 of income gives a DTI of 40%.
  - High DTI means the borrower is more financially stretched, and prepays slightly more slowly.
- **Mortgage insurance (MI / PMI):** insurance the borrower pays when LTV is above 80%. It protects the lender if the borrower defaults.
- **Loan purpose:** *Purchase* (buying a home), *Cash-out refi* (refinancing while borrowing extra cash against equity), or *Rate/term refi* (refinancing only to change the rate or term).
- **Occupancy:** *Primary* residence, *Second home*, or *Investor* (rental property).
- **Channel:** how the loan reached Fannie Mae. *Retail* means originated directly by the lender, *Broker* means arranged through a mortgage broker, and *Correspondent* means originated by a smaller lender and sold on.
- **First-time buyer:** the borrower has not owned a home before.
- **Loan age:** months since the first payment. A **seasoned** loan is an older one.
- **Vintage:** the year the loan was originated. Loans from the same vintage share similar rates and market conditions.

## Rate incentive

- **Market rate (prevailing rate):** the rate a borrower could get on a new 30-year mortgage today.
  - The project has no official rate series yet. As a **proxy**, we use the size-weighted average rate on 30-year loans **originated** in each month (the `mkt` table in the notebook).
- **Refi incentive:** how much a borrower could save by refinancing.
  - `incentive = loan's note rate - market rate (previous month)`
  - We use the previous month's rate because a refinance takes a few weeks, so a payoff this month was decided on last month's rates.
  - **Example:** a 5.5% loan when the market is 3.0% has an incentive of **+2.5**. The same loan when the market is 6.5% has an incentive of **-1.0**.
- **Basis point (bp):** 0.01 percentage points. 75bp = 0.75 points.
- **Moneyness:** a borrower effectively holds an **option** to refinance. These terms come from options trading.

  | Group | Incentive | Meaning |
  |---|---|---|
  | **Out of the money** | < 0 | Refinancing would raise the rate. Only home sales cause payoffs. |
  | **Near the money** | 0 to 0.75 | Small savings, often not worth the fees. Some borrowers refinance. |
  | **In the money** | ≥ 0.75 | Clear savings. Many borrowers refinance. |

  The 0.75 cutoff is a judgment call, based on a common rule of thumb that borrowers need 0.5 to 1 point of savings to cover refinancing costs.
- **LLPA (Loan-Level Price Adjustment):** an extra rate charged to riskier borrowers (low FICO, high LTV). Their note rates sit above the market average, so our incentive proxy **overstates** how much they would save by refinancing.

## Prepayment patterns

- **S-curve:** the shape of CPR plotted against refi incentive. It is flat and low when out of the money, rises steeply around 0 to +1 point, then levels off.
- **Turnover:** the baseline prepayment that comes from people moving house (sales), regardless of rates. In this data it runs at about 4 to 6% CPR.
- **Seasoning (age ramp):** new loans prepay slowly. Speeds build up over the first 1 to 2 years.
- **Burnout:** older loans respond less to a good rate. Borrowers who were able and willing to refinance already did so in earlier rate drops, and those left are less responsive.
- **Mix effect:** a pooled average can hide or fake a relationship, because different groups of loans faced different rate environments. Example: FICO looks flat when pooled, but matters a lot once you compare loans facing the same rates.
- **Relative speed:** a bucket's actual prepaid balance ÷ the balance we'd expect if it prepaid like all loans in the **same month and incentive bucket**. 1.0 means average, 1.2 means 20% faster than comparable loans.

## Analysis terms

- **Loan-month:** one row of the data, meaning one loan in one month. CPR is computed from loan-months.
- **1D analysis:** CPR split by **one** characteristic (e.g. CPR by FICO bucket).
- **2D analysis:** CPR split by **two** characteristics at once (e.g. FICO × LTV heatmap, or CPR vs. incentive with one line per FICO group). The CPR itself is the result, not a dimension.
- **Bucket:** a range a characteristic is grouped into (e.g. FICO 740-779).
- **95% band:** the range the true CPR likely falls in, given the sample size. A narrow band means a reliable estimate.

## Data fields (Fannie Mae loan performance file)

- **Zero Balance Code (field 44):** why a loan left the data. **01** = paid off (prepaid or matured). This is the event we count. 02/03/09/15 = third-party sale, short sale, deed-in-lieu or note sale (involuntary). 06 = repurchased by the lender. 16 = reperforming loan sale.
- **UPB at the Time of Removal (field 46):** the balance when the loan left. We use it as the prepaid amount.
- **Reference layout:** `references/crt-file-layout-and-glossary.pdf`. It is verified against `data/Performance_All.zip` (113 fields per row = PDF fields 1 to 113).
