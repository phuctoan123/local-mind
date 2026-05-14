from io import BytesIO
from zipfile import ZipFile

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
    with ZipFile(buffer, "w") as archive:
        archive.writestr("payload.txt", "hello")

    result = validate_file_signature("notes.docx", buffer.getvalue())

    assert not result.is_valid
    assert result.error == "invalid_file_signature"


def test_plain_text_is_accepted():
    result = validate_file_signature("notes.txt", b"Xin chao LocalMind\n")

    assert result.is_valid


def test_binary_data_disguised_as_txt_is_rejected():
    result = validate_file_signature("notes.txt", b"\x00\x01\x02\x03binary")

    assert not result.is_valid
    assert result.error == "invalid_file_signature"


def _docx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")
    return buffer.getvalue()
