from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str
    metadata: dict


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> list[ParsedPage]:
        """Parse a document file into page-like text sections."""


def parser_for_mime_type(mime_type: str) -> BaseParser:
    from app.ingestion.parsers.docx_parser import DocxParser
    from app.ingestion.parsers.pdf_parser import PdfParser
    from app.ingestion.parsers.txt_parser import TxtParser

    registry: dict[str, type[BaseParser]] = {
        "application/pdf": PdfParser,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser,
        "text/plain": TxtParser,
    }
    try:
        return registry[mime_type]()
    except KeyError as exc:
        raise ValueError(f"Unsupported mime type: {mime_type}") from exc
