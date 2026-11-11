# V4Career JobSpy isolated test

This is a separate test path. The existing Apify runner, free-source collector, database schema, Flask UI, and production `requirements.txt` are unchanged.

## What JobSpy can test

The JobSpy project currently documents support for Indeed and Naukri, along with LinkedIn, Glassdoor, ZipRecruiter, Bayt, BDJobs, and HelloWork. It does **not** document native adapters for TimesJobs, Foundit, Internshala, or Wellfound. Do not assume unsupported portals are covered.

JobSpy is third-party open-source software, but source sites can block requests or change their pages. Follow each portal's current terms and do not use the test to bypass access controls. A zero-result response may mean no matches, a parser issue, or a block; inspect errors/warnings.

## 1. Keep this package separate

Extract this ZIP into a new folder, for example `V4Career_JobSpy_Test_Package`. Do not overwrite the currently working project. The backup ZIP supplied alongside this package is a separate copy of the current free-collector project.

## 2. Install test-only dependency

From the test folder in PowerShell:

```powershell
python -m pip install -r requirements-jobspy-test.txt
```

The main `requirements.txt` was intentionally not changed, so the production deployment does not gain a new dependency.

## 3. Run a small South India test

Start with Bengaluru and a small result cap:

```powershell
python scripts/test_jobspy_sources.py --sites indeed,naukri --keyword "Software Engineer" --location Bengaluru --results 10
```

Then test another role/location after reviewing the first output:

```powershell
python scripts/test_jobspy_sources.py --sites indeed,naukri --keyword "Python Developer" --location Chennai --results 10
python scripts/test_jobspy_sources.py --sites indeed,naukri --keyword "Java Developer" --location Hyderabad --results 10
python scripts/test_jobspy_sources.py --sites indeed,naukri --keyword "Graduate Engineer Trainee" --location Coimbatore --results 10
```

## 4. Where test results go

The script writes only local CSV/JSON files to `jobspy_test_results/`. It does not import V4Career's database repository, read `.env`, or write to Neon/MySQL. Inspect `jobspy_test_report.json` for per-site rows, warnings, and errors.

## 5. What to report back

Share the terminal summary and counts for each site. Do not upload credentials. If the results are usable, the next step is a separate adapter that maps JobSpy fields to V4Career's existing normalized schema, still with dry-run as the default. Database integration should happen only after validating the data and source permissions.
