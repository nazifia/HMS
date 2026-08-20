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


class EscposLogoTests(SimpleTestCase):
    """The logo raster block a thermal printer is asked to burn."""

    def _file(self, data):
        """Minimal stand-in for the FieldFile escpos_logo() is handed."""
        from io import BytesIO
        from types import SimpleNamespace

        return SimpleNamespace(open=lambda mode="rb": BytesIO(data))

    def _png(self, w, h):
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (w, h), "black").save(buf, "PNG")
        return buf.getvalue()

    def _parse(self, blob):
        import base64

        raw = base64.b64decode(blob)
        self.assertTrue(raw.startswith(b"\x1b\x61\x01\x1d\x76\x30\x00"), raw[:8])
        row_bytes = raw[7] + raw[8] * 256
        height = raw[9] + raw[10] * 256
        body = raw[11:-4]  # trailing feed + left-align
        self.assertEqual(len(body), row_bytes * height)
        return row_bytes * 8, height

    def test_small_logo_is_not_upscaled(self):
        from core.receipts import escpos_logo

        # 100px wide on a 384-dot roll stays 100, padded up to a whole byte.
        self.assertEqual(
            self._parse(escpos_logo(self._file(self._png(100, 40)), "58")), (104, 40)
        )

    def test_oversized_logo_is_clamped_to_height(self):
        from core.receipts import escpos_logo, MAX_LOGO_DOTS

        width, height = self._parse(
            escpos_logo(self._file(self._png(1000, 1000)), "80")
        )
        self.assertEqual(height, MAX_LOGO_DOTS)
        self.assertLessEqual(width, 576)

    def test_no_logo_and_broken_logo_are_silent(self):
        from core.receipts import escpos_logo

        self.assertEqual(escpos_logo(None, "80"), "")
        self.assertEqual(escpos_logo(self._file(b"not an image"), "80"), "")
