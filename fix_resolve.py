from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

start = s.find('@app.route("/api/resolve-account", methods=["POST"])')

if start == -1:
    print("ERROR: resolve-account route not found.")
    raise SystemExit

end = s.find('@app.route(', start + 10)

if end == -1:
    end = len(s)

new_function = '''@app.route("/api/resolve-account", methods=["POST"])
def resolve_account():
    if not current():
        return jsonify({"status": False, "message": "Login required"}), 401

    data = request.get_json(silent=True) or {}

    destination = (data.get("destination") or "").strip()
    account_number = (data.get("account_number") or "").strip()
    bank_code = (data.get("bank_code") or "").strip()

    if destination not in {"Bank account", "OPay", "PalmPay", "Moniepoint"}:
        return jsonify({
            "status": False,
            "message": "Invalid withdrawal destination"
        }), 400

    if not account_number.isdigit() or not (10 <= len(account_number) <= 20):
        return jsonify({
            "status": False,
            "message": "Enter a valid account number"
        }), 400

    if not bank_code:
        return jsonify({
            "status": False,
            "message": "Select a bank before verifying"
        }), 400

    secret = os.environ.get("PAYSTACK_SECRET_KEY", "").strip()

    if not secret:
        return jsonify({
            "status": False,
            "message": "Paystack is not configured on the server"
        }), 503

    query = urllib.parse.urlencode({
        "account_number": account_number,
        "bank_code": bank_code
    })

    req = urllib.request.Request(
        "https://api.paystack.co/bank/resolve?" + query,
        headers={
            "Authorization": "Bearer " + secret,
            "Accept": "application/json",
            "User-Agent": "NovaEarn/1.0"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(
                e.read().decode("utf-8")
            )
        except Exception:
            payload = {
                "status": False,
                "message": "Paystack verification failed"
            }

        return jsonify({
            "status": False,
            "message": payload.get(
                "message",
                "Paystack verification failed"
            )
        }), 400

    except Exception as e:
        return jsonify({
            "status": False,
            "message": "Could not reach Paystack. Try again."
        }), 502

    if (
        payload.get("status") is True
        and isinstance(payload.get("data"), dict)
        and payload["data"].get("account_name")
    ):
        return jsonify({
            "status": True,
            "message": "Account verified",
            "account_name": payload["data"]["account_name"],
            "account_number": payload["data"].get(
                "account_number",
                account_number
            ),
            "bank_code": bank_code
        })

    return jsonify({
        "status": False,
        "message": payload.get(
            "message",
            "Account could not be verified"
        )
    }), 400

'''

s = s[:start] + new_function + s[end:]

p.write_text(s, encoding="utf-8")

print("resolve-account function replaced successfully.")