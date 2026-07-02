from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import docx
from docx.oxml.ns import qn

from schema.models import Chunk

_DATE_PAT = re.compile(r"^\**\s*(20\d{6})\s*\**$")
_SECTION_PAT = re.compile(r"^(\d+)\.\s+(.+)")


def _extract_lines(path: str) -> list[str]:
    doc = docx.Document(path)
    lines: list[str] = []
    for elem in doc.element.body:
        tag = elem.tag.split("}")[-1]
        if tag == "p":
            text = "".join(r.text for r in elem.iter(qn("w:t")))
            lines.append(text)
        elif tag == "tbl":
            for row in elem.iter(qn("w:tr")):
                for cell in row.iter(qn("w:tc")):
                    cell_text = "".join(r.text for r in cell.iter(qn("w:t")))
                    if cell_text.strip():
                        lines.append(cell_text)
    return lines


def _split_by_dates(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Return [(week_key, [lines_in_block]), ...], most-recent first."""
    boundaries: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = _DATE_PAT.match(line.strip())
        if m:
            boundaries.append((i, m.group(1)))

    blocks: list[tuple[str, list[str]]] = []
    for idx, (start, week) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        block_lines = lines[start + 1 : end]
        blocks.append((week, block_lines))
    return blocks


def _merge_consecutive_date_blocks(
    blocks: list[tuple[str, list[str]]]
) -> list[tuple[str, list[str]]]:
    """
    The top of the file has two date stamps close together (20251102/20251026)
    with the real content under 20251026. Merge a block that has almost no
    content (< 5 non-empty lines) into the next block, keeping the earlier
    (more-recent) date as the week key.
    """
    merged: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(blocks):
        week, lines_block = blocks[i]
        non_empty = [l for l in lines_block if l.strip()]
        if len(non_empty) < 5 and i + 1 < len(blocks):
            next_week, next_lines = blocks[i + 1]
            merged.append((week, lines_block + next_lines))
            i += 2
        else:
            merged.append((week, lines_block))
            i += 1
    return merged


def _split_into_chunks(week: str, lines: list[str]) -> list[Chunk]:
    """Split a week block by numbered section headers into Chunks."""
    chunks: list[Chunk] = []
    current_title = "intro"
    current_lines: list[str] = []

    for line in lines:
        m = _SECTION_PAT.match(line.strip())
        if m:
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    chunk_id = f"{week}#{current_title}"
                    chunks.append(Chunk(chunk_id=chunk_id, week=week,
                                        section_title=current_title, text=text))
            current_title = m.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            chunk_id = f"{week}#{current_title}"
            chunks.append(Chunk(chunk_id=chunk_id, week=week,
                                section_title=current_title, text=text))
    return chunks


def load_chunks(docx_path: str, weeks: int = 5) -> list[Chunk]:
    """Load and chunk the top `weeks` weeks from the docx archive."""
    lines = _extract_lines(docx_path)
    blocks = _split_by_dates(lines)
    blocks = _merge_consecutive_date_blocks(blocks)
    blocks = blocks[:weeks]

    all_chunks: list[Chunk] = []
    for week, block_lines in blocks:
        chunks = _split_into_chunks(week, block_lines)
        all_chunks.extend(chunks)
    return all_chunks


if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else "data/examples/Tech周报_讨论.docx"
    chunks = load_chunks(path)
    print(f"Loaded {len(chunks)} chunks from {len(set(c.week for c in chunks))} weeks")
    for c in chunks:
        print(f"  [{c.week}] {c.chunk_id!r}  ({len(c.text)} chars)")
