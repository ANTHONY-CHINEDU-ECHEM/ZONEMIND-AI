"""Load, validate and chunk the knowledge base.

Every document is a Markdown file with YAML front matter. The prose is what gets
retrieved and shown to the language model. The front matter carries the same guidance
in machine readable form: ``directives`` for the deterministic reasoner and
``constraints`` for the verifier. Keeping both in one governed file means an operations
team edits policy in one place and the control behaviour follows.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..safe_eval import validate
from ..variables import VARIABLE_NAMES
from .schema import Chunk, Constraint, Directive, Document

_FRONT = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


class KnowledgeBase:
    def __init__(self, docs: list[Document]):
        self.docs = {d.id: d for d in docs}
        if len(self.docs) != len(docs):
            raise ValueError("duplicate document ids in the knowledge base")
        self.chunks: list[Chunk] = [c for d in docs for c in chunk_document(d)]
        self.constraints: list[Constraint] = [c for d in docs for c in d.constraints]
        self.directives: list[Directive] = [x for d in docs for x in d.directives]

    def __len__(self) -> int:
        return len(self.docs)

    def stats(self) -> dict:
        cats: dict[str, int] = {}
        for d in self.docs.values():
            cats[d.category] = cats.get(d.category, 0) + 1
        return {"documents": len(self.docs), "chunks": len(self.chunks),
                "directives": len(self.directives), "constraints": len(self.constraints),
                "words": sum(len(d.body.split()) for d in self.docs.values()), "by_category": cats}


def parse_document(text: str, source: str = "") -> Document:
    match = _FRONT.match(text.strip() + "\n")
    if not match:
        raise ValueError(f"{source}: missing YAML front matter")
    meta = yaml.safe_load(match.group(1))
    doc_id = str(meta["id"])
    directives = []
    for i, raw in enumerate(meta.get("directives") or []):
        d = Directive(id=raw.get("id", f"{doc_id}_D{i + 1}"), doc_id=doc_id, priority=int(raw["priority"]),
                      label=raw.get("label", doc_id), when=str(raw["when"]), set=dict(raw.get("set") or {}),
                      lockout=bool(raw.get("lockout", False)))
        validate(d.when, VARIABLE_NAMES)
        for key, expr in d.set.items():
            if key not in ("heat", "cool"):
                raise ValueError(f"{source}: directive {d.id} sets unknown target '{key}'")
            validate(expr, VARIABLE_NAMES)
        directives.append(d)
    constraints = []
    for raw in meta.get("constraints") or []:
        c = Constraint(doc_id=doc_id, **raw)
        if c.kind not in ("bound", "gap", "rate", "flag"):
            raise ValueError(f"{source}: constraint {c.id} has unknown kind '{c.kind}'")
        validate(c.when, VARIABLE_NAMES)
        constraints.append(c)
    return Document(id=doc_id, title=str(meta["title"]), category=str(meta["category"]),
                    tags=list(meta.get("tags") or []), body=match.group(2).strip(),
                    directives=directives, constraints=constraints)


def chunk_document(doc: Document) -> list[Chunk]:
    """Split a document on second level headings, keeping the title in every chunk.

    Repeating the title and tags gives each chunk enough context to be retrieved and read
    on its own, which matters more than chunk size for short operational documents.
    """
    parts = re.split(r"^## +", doc.body, flags=re.M)
    chunks = []
    for i, part in enumerate(p for p in parts if p.strip()):
        lines = part.strip().split("\n", 1)
        heading = lines[0].lstrip("# ").strip() if len(lines) > 1 else "Overview"
        content = lines[1].strip() if len(lines) > 1 else lines[0].strip()
        text = f"{doc.title}. {heading}. {content}"
        if i == 0 and doc.tags:
            text += " Keywords: " + ", ".join(doc.tags) + "."
        chunks.append(Chunk(id=f"{doc.id}#{i}", doc_id=doc.id, heading=heading, text=text))
    return chunks


def load_knowledge_base(folder: str | Path) -> KnowledgeBase:
    files = sorted(Path(folder).glob("*.md"))
    if not files:
        raise FileNotFoundError(f"no knowledge documents found in {folder}")
    return KnowledgeBase([parse_document(f.read_text(encoding="utf-8"), f.name) for f in files])
