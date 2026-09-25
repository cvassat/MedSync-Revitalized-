# MedSync7

Single-page Streamlit app that calculates how many units of each medication a
patient needs so that every prescription, including a new one, refills on the
same date. Sign-in is handled by Supabase Auth (email and password).

## Run Locally

```bash
pip install -r requirements.txt
streamlit run med_sync_app_final.py   # opens at http://localhost:8501
```

## Configuration

The app reads its Supabase project from, in order:

1. `SUPABASE_URL` and `SUPABASE_KEY` environment variables
2. The same keys in `.streamlit/secrets.toml`
3. A built-in default pointing at the shared MedSync7 project

Only the public anon key is used, and row-level security restricts each user to
their own rows. Set your own values for any deployment you control.

## Development

```bash
pip install -r requirements-dev.txt
flake8 .      # scope and limits come from .flake8
pytest        # unit tests for the sync calculation
```

CI runs the same lint and test steps on every push and pull request.

## Enterprise Readiness Improvements

- Defensive input validation for login, sign-up, and medication fields
- Safe sync-date parsing and validation with user-facing errors instead of crashes
- Session logout action in the authenticated calculator view
- Sanitized authentication error messages (detailed stack traces stay in logs)
- Expanded unit tests for invalid and incomplete calculator inputs

## How the Calculation Works

For each existing medication:

```
days_left  = units_remaining // daily_dose
additional = days_until_sync - days_left
units      = max(additional * daily_dose, 0)
```

A new medication has no supply on hand, so it always needs
`daily_dose * days_until_sync` units. Days are counted as whole calendar days,
and the sync date must be after today.
