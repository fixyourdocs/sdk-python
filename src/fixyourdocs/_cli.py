"""``fixyourdocs`` CLI — ``init`` + ``report`` subcommands.

Exit codes:

* ``0`` — success.
* ``2`` — user / argument error (unknown / missing flag, bad enum).
* ``1`` — transport or server error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Optional

from fixyourdocs import __version__
from fixyourdocs._init import run_init
from fixyourdocs.client import Client
from fixyourdocs.errors import FixYourDocsError
from fixyourdocs.models import Report, ReportKind

DEFAULT_API_URL = "https://hub.fixyourdocs.io"
_REPORT_KINDS = tuple(k.value for k in ReportKind)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fixyourdocs",
        description=(
            "FixYourDocs CLI — adds the canonical AGENTS.md block to your "
            "repo and sends Docs Feedback Protocol v0 reports."
        ),
    )
    parser.add_argument(
        "-v", "--version", action="version", version=__version__
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    init_p = sub.add_parser(
        "init",
        help="Append the canonical AGENTS.md block to your repo.",
    )
    init_p.add_argument(
        "--file",
        help=(
            "Explicit target file (skips auto-detection of AGENTS.md / "
            "CLAUDE.md / .cursor/rules / .github/copilot-instructions.md)."
        ),
    )
    init_p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of plain text.",
    )

    rep = sub.add_parser(
        "report",
        help="Send a Docs Feedback Protocol v0 report to the Hub.",
    )
    rep.add_argument("--doc-url", required=True)
    rep.add_argument("--summary", required=True)
    rep.add_argument("--agent", required=True, dest="agent_name")
    rep.add_argument(
        "--kind",
        choices=_REPORT_KINDS,
        default="other",
    )
    rep.add_argument("--details")
    rep.add_argument("--suggested-fix", dest="suggested_fix")
    rep.add_argument("--api-url", default=DEFAULT_API_URL, dest="api_url")
    rep.add_argument("--token")
    rep.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of plain text.",
    )
    return parser


def _do_init(args: argparse.Namespace, stdout: IO[str]) -> int:
    result = run_init(cwd=Path.cwd(), file=args.file)
    if args.json:
        stdout.write(
            json.dumps(
                {
                    "path": str(result.path),
                    "changed": result.changed,
                    "created": result.created,
                }
            )
            + "\n"
        )
    elif result.created:
        stdout.write(f"Created {result.path} with the FixYourDocs snippet.\n")
    elif result.changed:
        stdout.write(
            f"Appended the FixYourDocs snippet to {result.path}.\n"
        )
    else:
        stdout.write(
            f"No changes — snippet already present in {result.path}.\n"
        )
    return 0


def _do_report(
    args: argparse.Namespace, stdout: IO[str], stderr: IO[str]
) -> int:
    try:
        report = Report.create(
            doc_url=args.doc_url,
            summary=args.summary,
            kind=args.kind,
            agent_name=args.agent_name,
            details=args.details,
            suggested_fix=args.suggested_fix,
        )
    except (ValueError, FixYourDocsError) as err:
        stderr.write(f"error: {err}\n")
        return 2

    api_url = args.api_url.rstrip("/")
    with Client(api_url, token=args.token) as client:
        try:
            result = client.send(report)
        except FixYourDocsError as err:
            if args.json:
                stdout.write(
                    json.dumps(
                        {"error": type(err).__name__, "message": str(err)}
                    )
                    + "\n"
                )
            else:
                stderr.write(f"error: {err}\n")
            return 1

    if args.json:
        stdout.write(
            json.dumps(
                {
                    "id": result.id,
                    "received_at": result.received_at.isoformat(),
                    "is_duplicate": result.is_duplicate,
                    "url": f"{api_url}/r/{result.id}",
                }
            )
            + "\n"
        )
    else:
        label = "Duplicate report" if result.is_duplicate else "Report accepted"
        stdout.write(f"{label}: {result.id}\n")
        stdout.write(f"View: {api_url}/r/{result.id}\n")
    return 0


def run_cli(
    argv: Optional[Sequence[str]] = None,
    *,
    stdout: Optional[IO[str]] = None,
    stderr: Optional[IO[str]] = None,
) -> int:
    """Entry point used by both the console_script and the tests.

    Returns the desired process exit code; never calls ``sys.exit``
    itself.
    """
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr

    parser = _build_parser()
    # argparse calls sys.exit on errors; intercept to map to our exit codes.
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    if args.command is None:
        parser.print_help(out)
        return 0
    if args.command == "init":
        return _do_init(args, out)
    if args.command == "report":
        return _do_report(args, out, err)
    err.write(f"error: unknown command {args.command!r}\n")
    return 2


def main() -> None:  # console_script entry point
    sys.exit(run_cli(sys.argv[1:]))
