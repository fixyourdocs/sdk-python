# fixyourdocs (Python SDK)

Reference Python SDK for the [Docs Feedback Protocol](https://github.com/fixyourdocs/protocol)
v0. The protocol lets AI agents file structured reports against
documentation pages when the docs break agent task flows.

- Spec: <https://docsfeedback.org>.
- Why this exists: [the FixYourDocs manifesto](https://github.com/fixyourdocs/manifesto/blob/main/MANIFESTO.md).

## Install

```sh
pip install fixyourdocs
```

Requires Python 3.9+.

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
