"""``fixyourdocs init`` — append the canonical AGENTS.md block."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fixyourdocs.snippet import SNIPPET, SNIPPET_HEADING

TARGET_CANDIDATES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursor/rules",
    ".github/copilot-instructions.md",
)


@dataclass(frozen=True)
class InitResult:
    path: Path
    changed: bool
    created: bool


def _pick_default_target(cwd: Path) -> str:
    for candidate in TARGET_CANDIDATES:
        if (cwd / candidate).exists():
            return candidate
    return "AGENTS.md"


def _with_trailing_blank_line(s: str) -> str:
    if not s:
        return ""
    if s.endswith("\n\n"):
        return s
    if s.endswith("\n"):
        return s + "\n"
    return s + "\n\n"


def run_init(cwd: Path, file: Optional[str] = None) -> InitResult:
    """Append the canonical AGENTS.md block to the chosen target file.

    Idempotent: if the block heading is already present, returns
    ``InitResult(changed=False)`` and leaves the file untouched.
    """
    target_rel = file if file is not None else _pick_default_target(cwd)
    path = (cwd / target_rel).resolve()

    if not path.exists():
        path.write_text(SNIPPET)
        return InitResult(path=path, changed=True, created=True)

    current = path.read_text()
    if SNIPPET_HEADING in current:
        return InitResult(path=path, changed=False, created=False)

    path.write_text(_with_trailing_blank_line(current) + SNIPPET)
    return InitResult(path=path, changed=True, created=False)
