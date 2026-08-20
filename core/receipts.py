"""Thermal-roll receipts, shared by every module that prints one.

A receipt is a plain dict, so any view can render one without a model change:

    from core.receipts import wants_thermal, render_thermal

    if wants_thermal(request):
        return render_thermal(
            request,
            title="PAYMENT RECEIPT",
            meta=[("Receipt", "PH-12"), ("Date", payment.payment_date)],
            items=[{"name": "Paracetamol 500mg", "qty": 2, "unit": 150, "amount": 300}],
            totals=[("TOTAL", 300, True)],
        )

The same call also produces a plain 32/48-column text body, embedded in the
page for the webview print bridge to feed straight to an ESC/POS printer
(see static/js/print.js).
"""

import textwrap
from django.shortcuts import render

# 58mm rolls fit 32 characters at font A, 80mm rolls fit 48.
COLUMNS = {"58": 32, "80": 48}


def wants_thermal(request):
    return (request.GET.get("format") or "").lower() == "thermal"


def roll_width(request):
    return "58" if request.GET.get("width") == "58" else "80"


def money(value):
    """Amounts are printed without the Naira sign - most ESC/POS code pages
    have no glyph for it and print a blank or a garbage character instead."""
    try:
        return f"{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def fmt_dt(value):
    """Short date/time - a 32-column roll has no room for Django's default."""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%y %H:%M" if hasattr(value, "hour") else "%d/%m/%y")
    return value


def _pair(left, right, cols):
    """`left` flush left, `right` flush right, on one line (wraps if needed)."""
    left, right = str(left), str(right)
    if len(left) + len(right) + 1 <= cols:
        return left + " " * (cols - len(left) - len(right)) + right
    lines = textwrap.wrap(left, cols) or [""]
    lines.append(right.rjust(cols))
    return "\n".join(lines)


def _centered(text, cols):
    """Centered, wrapped to the roll - a long address must not run off the edge."""
    return [line.center(cols) for line in textwrap.wrap(str(text), cols)]


def receipt_text(title, meta, items, totals, header, footer, cols):
    """Plain-text receipt body for ESC/POS printers."""
    out = []
    for line in header:
        if line:
            out.extend(_centered(line, cols))
    out.extend(_centered(title, cols))
    out.append("-" * cols)
    for label, value in meta:
        if value not in (None, ""):
            out.append(_pair(f"{label}:", value, cols))
    out.append("-" * cols)
    for item in items:
        out.extend(textwrap.wrap(item["name"], cols) or [""])
        qty = item.get("qty")
        unit = item.get("unit")
        left = f"{qty} x {money(unit)}" if qty is not None else money(unit)
        out.append(_pair("  " + left, money(item.get("amount")), cols))
        if item.get("note"):
            out.extend(textwrap.wrap("  " + item["note"], cols))
    out.append("-" * cols)
    for label, value, _bold in totals:
        out.append(_pair(label, money(value), cols))
    out.append("-" * cols)
    out.append("Amounts in NGN".center(cols))
    for line in footer:
        if line:
            out.extend(_centered(line, cols))
    return "\n".join(out)


def render_thermal(request, title, meta, items, totals, footer=None):
    """Render a receipt on a thermal roll (?format=thermal[&width=58][&auto=1])."""
    from saas.context_processors import hospital_details

    details = hospital_details(request)
    width = roll_width(request)
    cols = COLUMNS[width]
    header = [
        details["hospital_name"],
        details["hospital_address"],
        details["hospital_phone"],
    ]
    footer = footer or ["Computer-generated receipt", "Thank you!"]
    # Totals may arrive as (label, value) - default them to non-bold.
    totals = [t if len(t) == 3 else (t[0], t[1], False) for t in totals]

    return render(
        request,
        "includes/thermal_receipt.html",
        {
            "title": title,
            "meta": [(k, v) for k, v in meta if v not in (None, "")],
            "items": items,
            "totals": totals,
            "header_lines": [h for h in header if h],
            "footer_lines": footer,
            "roll_width": width,
            "auto_print": request.GET.get("auto") == "1",
            "receipt_text": receipt_text(
                title, meta, items, totals, header, footer, cols
            ),
        },
    )


def payment_receipt_response(request, context):
    """Return the A4 payment receipt, or its thermal twin on ?format=thermal.

    Reads the context the payment-receipt views already build, so wiring a view
    up is a one-line change at its final `return render(...)`.
    """
    if not wants_thermal(request):
        return render(request, "payments/payment_receipt.html", context)

    payment = context.get("payment")
    invoice = context.get("invoice")
    patient = context.get("patient")
    items = [
        {
            "name": i.get("description") or "Item",
            "qty": i.get("quantity"),
            "unit": i.get("unit_price"),
            "amount": i.get("total"),
        }
        for i in context.get("items") or []
    ]
    totals = []
    if items:
        totals.append(("Subtotal", sum(float(i["amount"] or 0) for i in items), False))
    totals.append(("AMOUNT PAID", getattr(payment, "amount", 0), True))
    if invoice is not None and getattr(invoice, "get_balance", None):
        totals.append(("Balance", invoice.get_balance(), False))

    return render_thermal(
        request,
        title="PAYMENT RECEIPT",
        meta=[
            ("Receipt", context.get("receipt_number") or getattr(payment, "id", "")),
            ("Date", fmt_dt(getattr(payment, "payment_date", None))),
            ("Service", context.get("service_type")),
            ("Patient", patient.get_full_name() if patient else ""),
            ("Patient ID", getattr(patient, "patient_id", "")),
            ("Invoice", getattr(invoice, "invoice_number", "") if invoice else ""),
            ("Method", getattr(payment, "get_payment_method_display", lambda: "")()),
            ("Cashier", getattr(getattr(payment, "received_by", None), "get_full_name", lambda: "")()),
        ],
        items=items,
        totals=totals,
    )
