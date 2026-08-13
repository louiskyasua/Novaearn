from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

old = '''  if destination not in {"Bank account","OPay","PalmPay","Moniepoint"} or not destination_number.isdigit() or not account_name or not bank_code:
   flash("Verify the withdrawal account before submitting.");return redirect(url_for("withdraw"))
'''

new = '''  if destination not in {"Bank account","OPay","PalmPay","Moniepoint"} or not destination_number.isdigit():
   flash("Enter valid withdrawal destination details.");return redirect(url_for("withdraw"))
'''

if old not in s:
    print("Target block not found.")
else:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("Withdrawal verification requirement removed.")