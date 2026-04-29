from __future__ import annotations

from app.ingestion.parsers.base import BaseParser, ParsedPage


class PdfParser(BaseParser):
    def parse(self, file_path: str) -> list[ParsedPage]:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required to parse PDF files") from exc

        pages: list[ParsedPage] = []
        with fitz.open(file_path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                pages.append(ParsedPage(page_number=index, text=text, metadata={}))
        return pages
