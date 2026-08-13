from pathlib import Path

p = Path("app.py")
text = p.read_text(encoding="utf-8")

marker = '@app.route("/api/resolve-account", methods=["POST"])'

if '@app.route("/api/banks", methods=["GET"])' not in text:
    endpoint = '''@app.route("/api/banks", methods=["GET"])
def get_banks():
    if not current():
        return jsonify({"status": False, "message": "Login required"}), 401

    secret = os.environ.get("PAYSTACK_SECRET_KEY", "").strip()
    if not secret:
        return jsonify({"status": False, "message": "Paystack is not configured on the server"}), 503

    req = urllib.request.Request(
        "https://api.paystack.co/bank?country=nigeria&perPage=100",
        headers={
            "Authorization": "Bearer " + secret,
            "Accept": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"status": False, "message": "Paystack bank-list request failed"}
        return jsonify(payload), 502
    except Exception:
        return jsonify({"status": False, "message": "Could not reach Paystack"}), 502

    return jsonify(payload)

'''

    if marker not in text:
        raise SystemExit("Could not find /api/resolve-account in app.py")

    text = text.replace(marker, endpoint + marker, 1)
    p.write_text(text, encoding="utf-8")
    print("Bank endpoint added successfully.")
else:
    print("Bank endpoint already exists.")