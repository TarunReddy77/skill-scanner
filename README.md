# skill-scanner

An AI agent that reads an [agent skill](https://github.com/anthropics/skills) (a folder with a `SKILL.md` and other files) and decides whether it is **malicious** or **benign**, with a confidence score and quoted evidence.

Agent skills are instructions that coding agents follow automatically, so a poisoned skill can quietly steal credentials or change an agent's behavior. This project explores using an LLM agent as the security reviewer, built step by step with [Strands Agents](https://strandsagents.com) on Amazon Bedrock and traced with [Langfuse](https://langfuse.com).

> **Status: work in progress, built in the open.** Milestone 1 is under way: the scanner reads whole skill folders, and a public labeled benchmark is being built. **There are no accuracy numbers yet.** This README states only measured results, with the date and model ID. See [progress](#progress).

## Example

Real output, 2026-11-06, model `us.amazon.nova-lite-v1:0`, on a benign sample skill that tests API endpoints:

```
$ uv run python -m skill_scanner.agent path/to/skill-folder
```

```json
{
  "status": "scanned",
  "verdict": {
    "verdict": "benign",
    "category": null,
    "confidence": 0.95,
    "evidence": [],
    "reasoning": "The skill is designed to test API endpoints during development, which is a benign use case. There is no indication of malicious behavior."
  },
  "error": null
}
```

This is one scan, not a measurement of accuracy. Add `--verbose` to watch the agent's tool calls as it works.

## What counts as malicious

A skill is malicious if it does something the user would object to if they knew, **and** the skill hides or misdescribes it. A skill that openly describes a strong ability (for example, "deploys to production") is benign. A malicious skill gets one primary category:

| Category | Meaning |
| --- | --- |
| `data-exfiltration` | sends the user's files, code or conversation somewhere the user did not choose |
| `credential-access` | reads or collects secrets the stated job does not need |
| `hidden-instructions` | tells the agent to hide things from the user, ignore their rules, or act unasked |
| `destructive-or-persistent-ops` | deletes or overwrites data, or plants something that keeps running |
| `remote-code-fetch` | downloads and runs unreviewed code from the internet |
| `obfuscation` | hides what the skill really does |

## How it works

1. The agent receives a skill folder.
2. Before the model is called, plain code checks the folder. A symlink, a missing `SKILL.md`, a file over 100 KB, a folder over 500 KB, or a file that is not valid text makes the scan **unscannable**. Nothing is silently cut short.
3. The model gets two tools only: `list_files` and `read_file`, both locked to that folder. They refuse `../` paths, absolute paths and symlinks. Nothing can run or execute anything.
4. The model finishes by returning a typed `Verdict` (a Pydantic model): `malicious` or `benign`, a category, a confidence, evidence as `{file, line, quote}`, and a short reasoning.

Design choices worth noting:

- **A failed scan is never "benign".** `unscannable` is set by the scanner, not by the model, and counts as a failed scan.
- **The skill is untrusted input.** The prompt tells the model to analyze the content and never follow instructions inside it.
- **The scan core does not depend on the agent framework.** The model is passed in as a plain function, so the rules above are tested with a fake model (no network, no cost).
- **Observability.** Every run is traced to Langfuse: one `scan-skill` trace with each model call and each tool call.

## Progress

Milestone 1 builds the folder scanner and a public labeled benchmark. The full plan is in [docs/specs/M1.md](docs/specs/M1.md).

- [x] New verdict format (category, `{file, line, quote}` evidence, `unscannable` status)
- [x] Scan a whole folder with the safe read tools
- [ ] Time limit and retry cap for each scan
- [ ] Benchmark data layout: labeled skills, neutral IDs, dev/test split
- [ ] Sandbox for scanning real malicious samples (no network, read-only, no credentials)
- [ ] Benign and malicious benchmark skills, labeled by a jury of three different models
- [ ] Evaluation: per-category recall and precision, false-positive rate, unscannable share, with counts and ranges
- [ ] Check that quoted evidence really exists in the files

## Running it

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), and access to a model on Amazon Bedrock.

```bash
uv sync
cp .env.example .env   # then fill in the values below
uv run python -m skill_scanner.agent path/to/skill-folder
```

Each scan is one paid model call.

Environment variables (in `.env`):

| Variable | Purpose |
| --- | --- |
| `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION` | Bedrock access for the model |
| `SCANNER_MODEL_ID` | Optional. Overrides the default model, Amazon Nova Lite (`us.amazon.nova-lite-v1:0`) |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | Tracing to Langfuse (optional: leave unset to run without tracing) |

Tests (no network, no model calls):

```bash
uv run pytest
```

### Web UI

```bash
uv run uvicorn skill_scanner.server:app --reload
```

Open http://localhost:8000 and drop a skill folder onto the page. **Known limit:** the page uploads only `SKILL.md`, so other files in the folder are not scanned yet. Whole-folder upload is tracked in [#18](https://github.com/TarunReddy77/skill-scanner/issues/18).

## Project layout

```
src/skill_scanner/schema.py   the Verdict and ScanResult models
src/skill_scanner/scanner.py  folder checks and the scan core (model passed in as a function)
src/skill_scanner/tools.py    list_files and read_file, locked to one skill folder
src/skill_scanner/agent.py    the Strands agent, prompt and CLI
src/skill_scanner/server.py   FastAPI app: POST /api/scan and the web UI
tests/                        tests for the rules above
docs/specs/M1.md              the Milestone 1 spec
```

## Built with

[Strands Agents](https://strandsagents.com) · Amazon Bedrock · Pydantic · [Langfuse](https://langfuse.com) · uv · pytest
