from __future__ import annotations

import mimetypes
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.config import settings

MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def secure_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
    return name or "document"


def detect_mime_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in MIME_BY_EXTENSION:
        return MIME_BY_EXTENSION[suffix]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def extension_allowed(filename: str, allowed: tuple[str, ...]) -> bool:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix in allowed


@dataclass(frozen=True)
class FileSignatureValidation:
    is_valid: bool
    error: str = ""
    message: str = ""


def validate_file_signature(filename: str, contents: bytes) -> FileSignatureValidation:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _validate_pdf(contents)
    if suffix == ".docx":
        return _validate_docx(contents)
    if suffix == ".txt":
        return _validate_txt(contents)
    return FileSignatureValidation(
        is_valid=False,
        error="unsupported_format",
        message=f"File type is not supported: {filename}",
    )


def _validate_pdf(contents: bytes) -> FileSignatureValidation:
    if contents[:1024].lstrip().startswith(b"%PDF-"):
        return FileSignatureValidation(is_valid=True)
    return FileSignatureValidation(
        is_valid=False,
        error="invalid_file_signature",
        message="Uploaded PDF does not contain a valid PDF header.",
    )


def _validate_docx(contents: bytes) -> FileSignatureValidation:
    try:
        with zipfile.ZipFile(BytesIO(contents)) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
    except zipfile.BadZipFile:
        return FileSignatureValidation(
            is_valid=False,
            error="invalid_file_signature",
            message="Uploaded DOCX is not a valid Office document archive.",
        )

    zip_guard = _validate_zip_limits(infos)
    if not zip_guard.is_valid:
        return zip_guard

    required_entries = {"[Content_Types].xml", "word/document.xml"}
    if required_entries.issubset(names):
        return FileSignatureValidation(is_valid=True)
    return FileSignatureValidation(
        is_valid=False,
        error="invalid_file_signature",
        message="Uploaded DOCX is missing required Word document entries.",
    )


def _validate_zip_limits(infos: list[zipfile.ZipInfo]) -> FileSignatureValidation:
    if len(infos) > settings.max_docx_zip_entries:
        return FileSignatureValidation(
            is_valid=False,
            error="unsafe_archive",
            message="Uploaded DOCX archive contains too many files.",
        )

    uncompressed_size = sum(info.file_size for info in infos)
    max_uncompressed_bytes = settings.max_docx_uncompressed_mb * 1024 * 1024
    if uncompressed_size > max_uncompressed_bytes:
        return FileSignatureValidation(
            is_valid=False,
            error="unsafe_archive",
            message="Uploaded DOCX archive is too large after decompression.",
        )

    compressed_size = sum(max(info.compress_size, 1) for info in infos)
    if (
        uncompressed_size > 0
        and compressed_size > 0
        and uncompressed_size / compressed_size > settings.max_docx_compression_ratio
    ):
        return FileSignatureValidation(
            is_valid=False,
            error="unsafe_archive",
            message="Uploaded DOCX archive has an unsafe compression ratio.",
        )
    return FileSignatureValidation(is_valid=True)


def _validate_txt(contents: bytes) -> FileSignatureValidation:
    if b"\x00" in contents:
        return FileSignatureValidation(
            is_valid=False,
            error="invalid_file_signature",
            message="Uploaded TXT appears to be binary data.",
        )

    try:
        contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            import chardet

            detected = chardet.detect(contents)
            encoding = detected.get("encoding")
            confidence = float(detected.get("confidence") or 0)
            if not encoding or confidence < 0.6:
                raise UnicodeDecodeError("unknown", contents, 0, 1, "low confidence")
            contents.decode(encoding)
        except (ImportError, LookupError, UnicodeDecodeError):
            return FileSignatureValidation(
                is_valid=False,
                error="invalid_file_signature",
                message="Uploaded TXT could not be decoded as text.",
            )

    sample = contents[:4096]
    if not sample:
        return FileSignatureValidation(is_valid=True)

    allowed_controls = {9, 10, 12, 13}
    control_count = sum(byte < 32 and byte not in allowed_controls for byte in sample)
    if control_count / len(sample) > 0.05:
        return FileSignatureValidation(
            is_valid=False,
            error="invalid_file_signature",
            message="Uploaded TXT appears to contain too much binary control data.",
        )
    return FileSignatureValidation(is_valid=True)
