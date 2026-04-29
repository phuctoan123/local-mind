from __future__ import annotations

import mimetypes
import re
from pathlib import Path


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
