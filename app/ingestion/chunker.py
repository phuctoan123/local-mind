from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.parsers.base import ParsedPage


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    text: str
    token_count: int
    source_page: int
    char_start: int
    char_end: int
    metadata: dict


class RecursiveChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_length: int = 50,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length

    def chunk(self, pages: list[ParsedPage]) -> list[Chunk]:
        page_offsets: list[tuple[int, int, int]] = []
        parts: list[str] = []
        cursor = 0
        for page in pages:
            text = page.text.strip()
            if not text:
                continue
            start = cursor
            parts.append(text)
            cursor += len(text)
            page_offsets.append((start, cursor, page.page_number))
            parts.append("\f")
            cursor += 1

        text = "".join(parts).strip()
        if not text:
            return []

        max_chars = self.chunk_size * 4
        overlap_chars = self.chunk_overlap * 4
        step = max_chars - overlap_chars
        chunks: list[Chunk] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            if end < len(text):
                end = self._find_boundary(text, start, end)
            chunk_text = text[start:end].replace("\f", "\n").strip()
            if len(chunk_text) >= self.min_chunk_length:
                chunks.append(
                    Chunk(
                        chunk_index=len(chunks),
                        text=chunk_text,
                        token_count=estimate_tokens(chunk_text),
                        source_page=self._page_for_offset(page_offsets, start),
                        char_start=start,
                        char_end=end,
                        metadata={},
                    )
                )
            if end >= len(text):
                break
            start = max(end - overlap_chars, start + 1)
        return chunks

    @staticmethod
    def _find_boundary(text: str, start: int, end: int) -> int:
        window = text[start:end]
        for separator in ("\n\n", "\n", ". ", " "):
            idx = window.rfind(separator)
            if idx > len(window) * 0.5:
                return start + idx + len(separator)
        return end

    @staticmethod
    def _page_for_offset(page_offsets: list[tuple[int, int, int]], offset: int) -> int:
        for start, end, page_number in page_offsets:
            if start <= offset <= end:
                return page_number
        return page_offsets[-1][2] if page_offsets else 1


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)
