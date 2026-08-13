import json
import os
import sqlite3


ALLOWED_PAYMENT_PROVIDERS = {"OPay", "PalmPay", "Moniepoint"}
REFERRAL_BONUS = 500


def load_payment_accounts():
    raw = os.environ.get("NOVA_PAYMENT_ACCOUNTS_JSON", "").strip()

    if not raw:
        if os.environ.get("FLASK_ENV", "").lower() == "production":
            raise RuntimeError(
                "NOVA_PAYMENT_ACCOUNTS_JSON must be configured in production"
            )
        return []

    try:
        accounts = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("NOVA_PAYMENT_ACCOUNTS_JSON must contain valid JSON") from exc

    if not isinstance(accounts, list) or not accounts:
        raise RuntimeError("NOVA_PAYMENT_ACCOUNTS_JSON must be a non-empty JSON array")

    validated = []
    seen_providers = set()

    for account in accounts:
        if not isinstance(account, dict):
            raise RuntimeError("Each payment account must be a JSON object")

        provider = str(account.get("provider", "")).strip()
        account_number = str(account.get("account_number", "")).strip()

        if provider not in ALLOWED_PAYMENT_PROVIDERS:
            raise RuntimeError(f"Unsupported payment provider: {provider}")
        if provider in seen_providers:
            raise RuntimeError(f"Duplicate payment provider: {provider}")
        if not account_number or not account_number.isdigit():
            raise RuntimeError(f"Invalid account number for {provider}")

        seen_providers.add(provider)
        validated.append(
            {
                "provider": provider,
                "account_number": account_number,
            }
        )

    return validated


def install_referral_bonus_trigger():
    """Install the one-time ₦500 bonus trigger used on deposit activation.

    The trigger runs when an admin changes a deposit from pending to approved.
    A referred user can qualify only once, and the referrer's balance and
    transaction ledger are updated atomically with that approval.
    """
    db_path = os.environ.get("NOVA_DB_PATH")
    if not db_path:
        data_dir = os.environ.get("NOVA_DATA_DIR", "instance")
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "novaearn.db")

    if db_path == ":memory:":
        return

    connection = sqlite3.connect(db_path, timeout=10)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance INTEGER DEFAULT 0,
                created_at TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                role TEXT DEFAULT 'user',
                referral_bonus_awarded INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS deposits(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER,
                provider TEXT,
                reference TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT,
                amount INTEGER,
                note TEXT,
                created_at TEXT
            );
            """
        )

        user_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "referral_bonus_awarded" not in user_columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN referral_bonus_awarded INTEGER DEFAULT 0"
            )

        connection.execute("DROP TRIGGER IF EXISTS novaearn_referral_bonus")
        connection.execute(
            """
            CREATE TRIGGER novaearn_referral_bonus
            AFTER UPDATE OF status ON deposits
            WHEN NEW.status='approved' AND OLD.status <> 'approved'
            BEGIN
                UPDATE users
                SET balance = balance + 500
                WHERE id = (
                    SELECT referred_by FROM users WHERE id = NEW.user_id
                )
                AND id <> NEW.user_id
                AND EXISTS (
                    SELECT 1 FROM users
                    WHERE id = NEW.user_id
                      AND referred_by IS NOT NULL
                      AND COALESCE(referral_bonus_awarded, 0) = 0
                );

                INSERT INTO transactions(user_id, kind, amount, note, created_at)
                SELECT
                    id,
                    'REFERRAL_BONUS',
                    500,
                    '₦500 referral bonus',
                    datetime('now')
                FROM users
                WHERE id = (
                    SELECT referred_by FROM users WHERE id = NEW.user_id
                )
                AND changes() = 1;

                UPDATE users
                SET referral_bonus_awarded = 1
                WHERE id = NEW.user_id
                  AND referred_by IS NOT NULL
                  AND COALESCE(referral_bonus_awarded, 0) = 0;
            END;
            """
        )
        connection.commit()
    finally:
        connection.close()


PAYMENT_ACCOUNTS = load_payment_accounts()
install_referral_bonus_trigger()
