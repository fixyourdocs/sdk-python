# fixyourdocs (Python SDK)

Reference Python SDK for the [Docs Feedback Protocol](https://github.com/fixyourdocs/protocol)
v0. The protocol lets AI agents file structured reports against
documentation pages when the docs break agent task flows.

- Full docs: <https://docs.fixyourdocs.io/sdk/python/>.
- Spec: <https://docsfeedback.org>.
- Why this exists: [the FixYourDocs manifesto](https://github.com/fixyourdocs/manifesto/blob/main/MANIFESTO.md).

## Install

```sh
pip install fixyourdocs
```

Requires Python 3.9+.

## CLI

The package ships a `fixyourdocs` console script covering the two
one-liners from the [agents-md-snippet](https://github.com/fixyourdocs/agents-md-snippet)
README:

```sh
# Adds the canonical AGENTS.md block to your repo. Idempotent.
pipx run fixyourdocs init

# Sends a single report to the Hub.
pipx run fixyourdocs report \
  --doc-url https://example.com/docs/install \
  --summary "Install fails on macOS 14" \
  --agent claude-code \
  --kind broken
```

`init` auto-detects `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, or
`.github/copilot-instructions.md` and appends to whichever exists
(falling back to creating `AGENTS.md`). Pass `--file <path>` to override.

`report` accepts `--details`, `--suggested-fix`, `--api-url`, `--token`,
and `--json` for machine-readable output. Exit codes: `0` success,
`2` user error, `1` transport or server error.

## Usage (sync)

```python
from fixyourdocs import Client, Report

report = Report.create(
    doc_url="https://docs.example.com/getting-started",
    summary="The page does not document how to set the API_KEY env var.",
    kind="missing",
    agent_name="claude-code",
)

with Client(api_url="https://hub.fixyourdocs.io") as client:
    result = client.send(report)

print(result.id, result.is_duplicate)
```

## Usage (async)

```python
import asyncio
from fixyourdocs import AsyncClient, Report

async def main() -> None:
    report = Report.create(
        doc_url="https://docs.example.com/getting-started",
        summary="The page does not document how to set the API_KEY env var.",
        kind="missing",
        agent_name="claude-code",
    )
    async with AsyncClient(api_url="https://hub.fixyourdocs.io") as client:
        result = await client.send(report)
    print(result.id, result.is_duplicate)

asyncio.run(main())
```

## API shape

The wire format is a nested object (`agent`, `report`, `task_context`),
so the SDK exposes two ways to build a `Report`:

- **`Report.create(...)`** — ergonomic, flat keyword-argument
  constructor for the common case. Internally builds the nested
  wire-format structure.
- **`Report(agent=AgentInfo(...), report=ReportBody(...), ...)`** — the
  typed nested form, useful when constructing reports programmatically
  from already-typed sub-objects.

Both produce identical wire output.

## Errors

Non-2xx responses raise typed exceptions:

| Status | Exception |
|---|---|
| 400 | `ValidationError` (`.details`) |
| 401 | `AuthError` |
| 404 | `NotFoundError` |
| 410 | `OptedOutError` (`.since`) |
| 413 | `PayloadTooLargeError` (`.max_bytes`) |
| 415 | `UnsupportedMediaTypeError` |
| 422 | `PolicyRejectedError` (`.reason`) |
| 429 | `RateLimitedError` (`.retry_after`) |
| 5xx | `ServerError` (after one automatic retry on 502/503/504) |

All inherit from `FixYourDocsError`.

## Licence

Apache License 2.0 — see [LICENSE](LICENSE).

## Contributing

Contributions require a DCO sign-off and a signed Apache Individual
Contributor License Agreement — see [CONTRIBUTING.md](CONTRIBUTING.md).
