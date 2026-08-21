"""Extension allowlists for user-uploaded files.

Uploads land under MEDIA_ROOT and are served back from the same origin as the
app. Without an allowlist a user can store an .html or .svg file and hand a
colleague a link that runs script in their authenticated session, so every
FileField takes one of these.

ImageField needs no validator here -- Pillow already rejects anything that is
not a decodable image.
"""

from django.core.validators import FileExtensionValidator

DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx", "txt", "csv", "xls", "xlsx"]
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp"]
SCAN_EXTENSIONS = ["dcm", "dicom"]

# Scanned IDs, lab results, maintenance certificates: a document or a photo of one.
validate_document_upload = FileExtensionValidator(
    allowed_extensions=DOCUMENT_EXTENSIONS + IMAGE_EXTENSIONS
)

# Radiology studies additionally arrive as DICOM.
validate_radiology_upload = FileExtensionValidator(
    allowed_extensions=DOCUMENT_EXTENSIONS + IMAGE_EXTENSIONS + SCAN_EXTENSIONS
)


def _selfcheck():
    from django.core.exceptions import ValidationError

    class _F:
        def __init__(self, name):
            self.name = name

    for bad in ("payload.html", "payload.svg", "shell.php", "x.pdf.html"):
        try:
            validate_document_upload(_F(bad))
        except ValidationError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{bad} should have been rejected")
    validate_document_upload(_F("result.pdf"))
    validate_radiology_upload(_F("study.dcm"))
    print("upload validators ok")


if __name__ == "__main__":
    import os
    import sys

    import django

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hms.settings")
    django.setup()
    _selfcheck()
