from __future__ import annotations

from pathlib import Path

from app.ingestion.parsers.base import BaseParser, ParsedPage


class TxtParser(BaseParser):
    def parse(self, file_path: str) -> list[ParsedPage]:
        data = Path(file_path).read_bytes()
        encoding = "utf-8"
        try:
            import chardet

            detected = chardet.detect(data)
            if detected.get("encoding") and float(detected.get("confidence") or 0) >= 0.8:
                encoding = detected["encoding"]
        except ImportError:
            pass
        text = data.decode(encoding, errors="replace")
        return _split_text_pages(text, page_size=3000)


def _split_text_pages(text: str, page_size: int) -> list[ParsedPage]:
    sections = [part.strip() for part in text.split("\n\n") if part.strip()]
    pages: list[ParsedPage] = []
    buffer = ""
    for section in sections or [text.strip()]:
        if len(buffer) + len(section) > page_size and buffer:
            pages.append(ParsedPage(len(pages) + 1, buffer.strip(), {"logical_page": True}))
            buffer = ""
        buffer += ("\n\n" if buffer else "") + section
    if buffer.strip():
        pages.append(ParsedPage(len(pages) + 1, buffer.strip(), {"logical_page": True}))
    return pages
