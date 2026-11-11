# V4Career Apify collector accounts

Configure three separate Apify account tokens in `.env` (never commit real tokens):

```dotenv
APIFY_API_TOKEN_COLLECTOR1=your_account_1_token
APIFY_API_TOKEN_COLLECTOR2=your_account_2_token
APIFY_API_TOKEN_COLLECTOR3=your_account_3_token
```

## Account groups and estimated costs (USD / 1,000 jobs)

| Account | Portal | Price |
|---|---|---:|
| 1 | CutShort | $0.80 |
| 1 | Wellfound | $0.50 |
| 1 | Unstop | $1.50 |
| 1 | Foundit | $1.80 |
| 2 | TimesJobs | $1.99 |
| 2 | NCS | $2.99 |
| 2 | Hirist | $1.99 |
| 3 | Instahyre | $1.35 |
| 3 | Freshersworld | $0.79 |
| 3 | Internshala | Not supplied |
| 3 | Shine | Not supplied |

## Run collector groups

```powershell
python scripts/run_source_apify.py --source COLLECTOR1 --keyword "Software Engineer" --location India --max-results 1000
python scripts/run_source_apify.py --source COLLECTOR2 --keyword "Software Engineer" --location India --max-results 1000
python scripts/run_source_apify.py --source COLLECTOR3 --keyword "Software Engineer" --location India --max-results 1000
```

Each portal must also have its `APIFY_ACCESS_APPROVED_<PORTAL_KEY>=true` setting after actor authorization/input is verified. Actor prices shown are user-provided estimates, not guaranteed current Apify charges.
