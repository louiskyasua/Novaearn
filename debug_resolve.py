from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

old = '''except urllib.error.HTTPError as e:
try: payload=json.loads(e.read().decode("utf-8"))
except Exception: payload={"status":False,"message":"Paystack verification failed"}'''

new = '''except urllib.error.HTTPError as e:
try:
    payload=json.loads(e.read().decode("utf-8"))
except Exception:
    payload={"status":False,"message":"Paystack verification failed"}'''

if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("Diagnostic patch applied.")
else:
    print("Target block not found.")