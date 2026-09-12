# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
pip install -r requirements.txt
streamlit run med_sync_app_final.py   # opens at http://localhost:8501

# Lint and test (what CI runs)
pip install -r requirements-dev.txt
flake8 .                              # scope and limits come from .flake8
pytest                                # test_med_sync.py
```

## Architecture

Single-page Streamlit app with Supabase Auth (email/password). No data is persisted beyond the auth session.

### File layout

| File | Purpose |
|---|---|
| `med_sync_app_final.py` | Entry point: Supabase client init, auth gate (`show_login`), medication sync calculator |
| `test_med_sync.py` | Pytest suite for `calculate_sync_quantities`; mocks `streamlit` and `supabase` before import |
| `requirements.txt` | Runtime deps: `streamlit`, `supabase` |
| `requirements-dev.txt` | Runtime deps plus `flake8` and `pytest` |
| `.flake8` | Lint scope (excludes `.claude/`) and limits |
| `.claude/skills/run-medsync7/` | Agent skill: launch, screenshot, and AppTest smoke driver |

### Auth flow

`st.session_state['user']` is set on successful `supabase.auth.sign_in_with_password`. The top-level `if/else` near the bottom of `med_sync_app_final.py` gates the entire app on this key. There is no logout — a page refresh clears session state.

### Core calculation (`calculate_sync_quantities`)

```python
days_left  = remaining // daily_dose
additional = days_until_sync - days_left
units      = max(additional * daily_dose, 0)
```

New medications have zero units on hand and always need `daily_dose * days_until_sync` units. `days_until_sync` is a whole-calendar-day difference (`date`, not `datetime`), and a sync date of today or earlier returns an empty list.

### Supabase configuration

`_setting()` resolves `SUPABASE_URL` and `SUPABASE_KEY` from the environment, then `st.secrets`, then the built-in defaults. The defaults are the public anon key for the shared project (safe under RLS). When defaults are in use the app logs a warning and shows a caption on the login page.

### Branch conventions

- `main` — stable
- `claude/<session-id>` — AI feature branches; open PR to `main`
