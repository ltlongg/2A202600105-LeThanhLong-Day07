from __future__ import annotations

import math
import re

import numpy as np


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class ParentchildChunker:
    """
    Helper chunker kept from the original file.

    It first creates larger parent chunks, then smaller child chunks inside them.
    """

    def __init__(self, chunk_parent_size: int = 1000, chunk_child_size: int = 200) -> None:
        self.chunk_parent_size = chunk_parent_size
        self.chunk_child_size = chunk_child_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_child_size:
            return [text]
        if len(text) <= self.chunk_parent_size:
            return [
                text[start : start + self.chunk_child_size]
                for start in range(0, len(text), self.chunk_child_size)
            ]

        parent_chunks: list[str] = []
        child_chunks: list[str] = []
        for start in range(0, len(text), self.chunk_parent_size):
            parent_chunk = text[start : start + self.chunk_parent_size]
            parent_chunks.append(parent_chunk)
            for child_start in range(0, len(parent_chunk), self.chunk_child_size):
                child_chunk = parent_chunk[child_start : child_start + self.chunk_child_size]
                child_chunks.append(child_chunk)
        return parent_chunks + child_chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\\n\\n", "\\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        separators = self.separators if self.separators else [""]
        return [chunk for chunk in self._split(text, separators) if chunk]

    def _split(self, current_text: str, remaining_separators: list[str]):
        current_text = current_text.strip()
        if not current_text:
            return
        if len(current_text) <= self.chunk_size:
            yield current_text
            return
        if not remaining_separators:
            yield from self._slice_text(current_text)
            return

        separator = remaining_separators[0]
        if separator == "":
            yield from self._slice_text(current_text)
            return

        pieces = [piece.strip() for piece in current_text.split(separator) if piece.strip()]
        if not pieces:
            return
        if len(pieces) == 1:
            yield from self._split(current_text, remaining_separators[1:])
            return

        buffer = ""
        for piece in pieces:
            candidate = piece if not buffer else f"{buffer}{separator}{piece}"
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer:
                yield buffer.strip()

            if len(piece) <= self.chunk_size:
                buffer = piece
            else:
                yield from self._split(piece, remaining_separators[1:])
                buffer = ""

        if buffer:
            yield buffer.strip()

    def _slice_text(self, text: str):
        for start in range(0, len(text), self.chunk_size):
            chunk = text[start : start + self.chunk_size].strip()
            if chunk:
                yield chunk


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """

    a_dot_b = _dot(vec_a, vec_b)
    a_norm = np.linalg.norm(vec_a)
    b_norm = np.linalg.norm(vec_b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return a_dot_b / (a_norm * b_norm)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        chunkers = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=min(50, max(0, chunk_size // 5))),
            "parent_child": ParentchildChunker(chunk_parent_size=chunk_size * 2, chunk_child_size=chunk_size),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        results: dict[str, dict] = {}
        for name, chunker in chunkers.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = sum(len(chunk) for chunk in chunks) / count if count else 0.0
            results[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return results


# if __name__ == "__main__":
#     text ="""
#         "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut "
#         "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco "
#         "laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in "
#         "voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat "
#         "non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
# """    
#     comparator = ChunkingStrategyComparator()
#     comparison_results = comparator.compare(text, chunk_size=100)
#     for strategy, metrics in comparison_results.items():
#         print(f"Strategy: {strategy}")
#         print(f"  Count: {metrics['count']}")
#         print(f"  Average Length: {metrics['avg_length']:.2f}")
#         print(f"  Chunks: {metrics['chunks']}\n")