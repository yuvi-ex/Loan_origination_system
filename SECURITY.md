# Security

This repository is a **demo**: a loan-origination workflow on a local Exasol Personal database, with synthetic data.
It is not production software and should not be deployed as one.

## Reporting a vulnerability

Please report security problems **privately**, not in a public issue: on GitHub, open the repository's **Security** tab
and choose **Report a vulnerability**. You will get an answer within a few working days.

## What the demo does with secrets

- Database logins, the source containers' passwords and the mock bureau's API key are generated during install into
  `secrets/` (git-ignored, mode 600) and never printed. No password is written in the code.
- The LOS service listens on `127.0.0.1` only and accepts JSON requests addressed to `127.0.0.1`/`localhost` only.
- Connections to Exasol Personal use TLS **without verifying the certificate**, because Exasol Personal serves a
  self-signed certificate on the local VM. Do not copy that setting to code that talks to a real Exasol cluster:
  verify the certificate there (see the comments in `service/xdb.py`).
- Amazon Textract is called with your own AWS credentials when present; `TEXTRACT=off` in `config.local.env` disables it.
