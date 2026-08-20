"""Thermal receipt text layout - the only bit with real logic in it."""

from django.test import SimpleTestCase

from core.receipts import receipt_text, COLUMNS


class ReceiptTextTests(SimpleTestCase):
    def _render(self, width="58", **kw):
        opts = dict(
            title="PAYMENT RECEIPT",
            meta=[("Receipt", "PH-12"), ("Empty", "")],
            items=[
                {"name": "Paracetamol 500mg tablets", "qty": 2, "unit": 150, "amount": 300},
                {"name": "Gauze", "qty": 1, "unit": 50, "amount": 50, "note": "NHIA 90%"},
            ],
            totals=[("TOTAL", 350, True)],
            header=["Demo Hospital", "12 A Very Long Clinic Road, Somewhere District, Lagos", None],
            footer=["Thank you!"],
            cols=COLUMNS[width],
        )
        opts.update(kw)
        return receipt_text(**opts)

    def test_never_exceeds_roll_width(self):
        for width, cols in COLUMNS.items():
            for line in self._render(width).splitlines():
                self.assertLessEqual(len(line), cols, f"{width}mm: {line!r}")

    def test_amounts_are_right_aligned_and_present(self):
        cols = COLUMNS["58"]
        lines = self._render().splitlines()
        total = [l for l in lines if l.startswith("TOTAL")][0]
        self.assertTrue(total.endswith("350.00"))
        self.assertEqual(len(total), cols)
        self.assertIn("2 x 150.00", "\n".join(lines))

    def test_blank_values_are_dropped(self):
        self.assertNotIn("Empty", self._render())

    def test_long_name_wraps_instead_of_truncating(self):
        text = self._render(
            items=[{"name": "Amoxicillin/Clavulanic acid 625mg film coated tablets",
                    "qty": 30, "unit": 95.5, "amount": 2865}]
        )
        self.assertIn("Amoxicillin", text)
        self.assertIn("2,865.00", text)
