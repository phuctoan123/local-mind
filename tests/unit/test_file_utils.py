from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.utils.file_utils import validate_file_signature


def test_valid_pdf_signature_is_accepted():
    result = validate_file_signature("report.pdf", b"%PDF-1.7\nbody")

    assert result.is_valid


def test_pdf_extension_with_non_pdf_contents_is_rejected():
    result = validate_file_signature("report.pdf", b"not actually a pdf")

    assert not result.is_valid
    assert result.error == "invalid_file_signature"


def test_valid_docx_archive_is_accepted():
    result = validate_file_signature("notes.docx", _docx_bytes())

    assert result.is_valid


def test_docx_extension_with_plain_zip_is_rejected():
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("payload.txt", "hello")

    result = validate_file_signature("notes.docx", buffer.getvalue())

    assert not result.is_valid
    assert result.error == "invalid_file_signature"


def test_docx_with_too_many_entries_is_rejected():
    restore = _override_setting("max_docx_zip_entries", 2)

    try:
        result = validate_file_signature(
            "notes.docx",
            _docx_bytes({"word/extra.xml": "<w:extra />"}),
        )
    finally:
        restore()

    assert not result.is_valid
    assert result.error == "unsafe_archive"


def test_docx_with_unsafe_compression_ratio_is_rejected():
    restore = _override_setting("max_docx_compression_ratio", 2)

    try:
        result = validate_file_signature(
            "notes.docx",
            _docx_bytes({"word/payload.txt": "A" * 100_000}),
        )
    finally:
        restore()

    assert not result.is_valid
    assert result.error == "unsafe_archive"


def test_plain_text_is_accepted():
    result = validate_file_signature("notes.txt", b"Xin chao LocalMind\n")

    assert result.is_valid


def test_binary_data_disguised_as_txt_is_rejected():
    result = validate_file_signature("notes.txt", b"\x00\x01\x02\x03binary")

    assert not result.is_valid
    assert result.error == "invalid_file_signature"


def _docx_bytes(extra_entries: dict[str, str] | None = None) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")
        for name, content in (extra_entries or {}).items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _override_setting(name: str, value):
    from app.config import settings

    original = getattr(settings, name)
    object.__setattr__(settings, name, value)

    def restore():
        object.__setattr__(settings, name, original)

    return restore
