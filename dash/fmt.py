"""Formatting shared by the console (hosted on dash-server) and the LOS service: Indian money, percentages, escaping."""
import html as _h

LABEL = {"APPLICATION": "Loan application form", "PAYSLIP": "Payslip", "ID_PROOF": "PAN card", "EMPLOYMENT_LETTER": "Employment letter"}


def esc(v):
    return _h.escape("" if v is None else str(v))


def inr(v, short=False):
    """Indian grouping: ₹12,00,000; short: ₹12.0 L / ₹1.37 Cr."""
    if v is None or v == "":
        return "–"
    v = float(v)
    if short:
        return f"₹{v / 1e7:.2f} Cr" if abs(v) >= 1e7 else f"₹{v / 1e5:.1f} L" if abs(v) >= 1e5 else f"₹{v:,.0f}"
    s = f"{abs(int(round(v))):d}"
    head, tail = s[:-3], s[-3:]
    while len(head) > 2:
        tail = head[-2:] + "," + tail
        head = head[:-2]
    return ("-" if v < 0 else "") + "₹" + (head + "," + tail if head else tail)


def pct(v, d=0):
    return "–" if v is None else f"{float(v) * 100:.{d}f}%"
