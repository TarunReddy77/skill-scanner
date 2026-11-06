# CLAUDE.md

## Working preferences

- Before asking for approval (e.g. to run a command or make a change), always say what you are doing and why, in plain language. The user cannot approve a command they don't understand.
- Always use ELI15 language ("explain like I'm 15") in any conversation: plain words, short sentences, and jargon explained when it can't be avoided.

## AWS and Amazon Bedrock AgentCore

Adapted from AWS's recommended rules file (https://github.com/aws/agent-toolkit-for-aws/blob/main/rules/aws-agent-rules.md). If these rules clash with something else in this file, this file wins.

### Good habits

- Before starting an AWS task, check if there is a relevant AWS skill (the `aws-core` and `aws-agents` plugins) and follow it instead of guessing.
- If you are not sure about an AWS detail (a setting, a permission, a limit, an error), look it up in the docs. If you still can't confirm it, say so.
- To create AWS things, write infrastructure as code (AWS CDK or CloudFormation). Don't build things one by one with CLI commands.
- Follow the AWS Well-Architected Framework (AWS's checklist for building safe and reliable systems).
- Don't use em dashes in AWS resource names or descriptions. Use hyphens.

### Secrets

- For any secret (password, API key, token), load the `aws-secrets-manager` skill first.
- Never call `secretsmanager get-secret-value` or `batch-get-secret-value`. That would put the secret into the chat.
- Never print, log, or write a secret value anywhere. This includes the Bedrock token in `.env`.

### Safety rules for deploying (added for this project)

- Never run a command that creates, changes, or deletes AWS things unless I say yes to that exact command first. This includes `agentcore deploy`, `cdk deploy`, and `cdk destroy`.
- Before any deploy, run `cdk diff` and show me the result in plain language. It lists what would change.
- Before any AWS command, tell me which AWS profile and region it will use.
- Before creating anything that costs money (for example AgentCore runtimes, memory, browser or code sessions), tell me it costs money and wait for a yes.
- The AgentCore MCP server in `.mcp.json` is docs-only on purpose. Don't turn on its other tool groups. If you think one is needed, ask me first.
- The `aws-mcp` server does not use my credentials and can only read docs. Don't switch to the AWS CLI "because the MCP server can't do it". Ask me first.

## Project context (launchpad)

This is one of Tarun's portfolio projects. Planning lives in ~/launchpad, which is private. Never copy its files into this repo.

- Current milestone brief: the newest `~/launchpad/briefs/M*-skill-scanner.md`. Read it before starting work.
- New milestone: run /grill-me on the brief, then /to-spec, /to-tickets, /tdd one issue at a time, and /code-review before each merge.
- Rules: build from scratch (no employer code, samples, prompts, or data). The README states only measured results, with the date and model ID. No em dashes in docs.
- When a milestone is done: update `~/launchpad/projects/skill-scanner.md` with what was built and the real numbers, tick it in `~/launchpad/analysis/project-plan.md`, and draft a resume bullet for Tarun to confirm. Don't edit `~/launchpad/cv.md` directly.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for TarunReddy77/skill-scanner (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
