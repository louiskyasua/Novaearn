# NovaEarn

NovaEarn is a Flask web application with accounts, wallet balances, deposits, withdrawals, referrals, investment plans and an administrator dashboard.

## Local Windows setup

1. Install Python 3.11+.
2. Open CMD in the project folder.
3. Install dependencies:
   `py -m pip install -r requirements.txt`
4. Start the app:
   `py app.py`
5. Open `http://127.0.0.1:5000`.

For local development, payment accounts are supplied with `NOVA_PAYMENT_ACCOUNTS_JSON`. The repository intentionally contains no live payment account numbers and no runtime database.

Example JSON format:

`[{"provider":"OPay","account_number":"0000000000"},{"provider":"PalmPay","account_number":"0000000000"}]`

Do not commit real account numbers, passwords or secret keys.

## Production deployment

The repository includes `render.yaml` for a Render web service. It uses Gunicorn, `/healthz` for health checks, and a persistent disk mounted at `/var/data` so the SQLite database is not lost on restart or deployment.

Configure these environment variables in the deployment dashboard:

- `NOVA_EARN_SECRET` — generated automatically by the Render blueprint.
- `NOVA_ADMIN_EMAIL` — administrator login email.
- `NOVA_ADMIN_PASSWORD` — administrator login password.
- `NOVA_PAYMENT_ACCOUNTS_JSON` — JSON array containing the active payment accounts.

`FLASK_ENV=production`, `NOVA_COOKIE_SECURE=1`, and `NOVA_DATA_DIR=/var/data` are already included in `render.yaml`.

## Important deployment notes

- The runtime database is created automatically on first start and is ignored by Git.
- Payment account numbers are deployment configuration, not source-code constants.
- Deposit and withdrawal approval operations are protected against processing the same pending record twice.
- Matured investments are settled once by changing the investment from `active` to `matured` inside the same database transaction that credits the maturity value.
- The application should be run behind HTTPS in production.
