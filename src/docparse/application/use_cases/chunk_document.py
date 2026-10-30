"""Section-aware packing of blocks into retrieval chunks. Tables are never split."""

from __future__ import annotations

from docparse.domain.models import Block, BlockKind, Chunk, Document


class ChunkDocument:
    def __init__(self, max_chars: int = 1500, overlap_blocks: int = 1) -> None:
        self.max_chars = max_chars
        self.overlap_blocks = overlap_blocks

    def __call__(self, document: Document) -> list[Chunk]:
        return _Packer(self.max_chars, self.overlap_blocks).pack(document)


class _Packer:
    def __init__(self, max_chars: int, overlap_blocks: int) -> None:
        self.max_chars, self.overlap_blocks = max_chars, overlap_blocks
        self.chunks: list[Chunk] = []
        self.buffer: list[Block] = []
        self.section: list[tuple[int, str]] = []  # (level, title)
        self.path: list[str] = []

    def pack(self, document: Document) -> list[Chunk]:
        for block in document.blocks:
            if block.kind is BlockKind.HEADING:
                self._heading(block)
            elif not block.is_empty:
                self._body(block)
        self._flush(keep_overlap=False)
        return self.chunks

    def _heading(self, block: Block) -> None:
        self._flush(keep_overlap=False)
        level = block.level or 2
        self.section = [(lv, t) for lv, t in self.section if lv < level] + [(level, block.text)]
        self.path = [t for _, t in self.section]
        self.buffer.append(block)

    def _body(self, block: Block) -> None:
        size = sum(len(b.to_markdown()) for b in self.buffer)
        if self.buffer and size + len(block.to_markdown()) > self.max_chars:
            self._flush(keep_overlap=True)
        self.buffer.append(block)

    def _flush(self, keep_overlap: bool) -> None:
        if not self.buffer:
            return
        text = "\n\n".join(b.to_markdown() for b in self.buffer).strip()
        if text:
            self.chunks.append(
                Chunk(
                    index=len(self.chunks),
                    text=text,
                    section_path=list(self.path),
                    provenance=[b.provenance for b in self.buffer],
                )
            )
        # ponytail: overlap = trailing block(s), not a char window; refine when evals show gaps
        tail = self.buffer[-self.overlap_blocks :] if keep_overlap and self.overlap_blocks else []
        self.buffer = [b for b in tail if b.kind is not BlockKind.HEADING]
