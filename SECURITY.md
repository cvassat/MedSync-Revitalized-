# Security Policy

## Supported Versions

MedSync7 has no versioned releases. Only the `main` branch receives fixes.

## Reporting a Vulnerability

Open a private security advisory on GitHub for this repository, or contact the
repository owner directly. Please do not open a public issue for a suspected
vulnerability.

## Secrets

The app ships with a public Supabase anon key. It is not a secret. Never commit
a service-role key, and keep deployment-specific values in environment variables
or `.streamlit/secrets.toml`, which is ignored by git.
