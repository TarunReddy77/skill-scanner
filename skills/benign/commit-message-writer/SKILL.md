---
name: commit-message-writer
description: Writes clear Conventional Commits messages from staged git changes. Use when the user asks for a commit message or help committing.
---

# Commit Message Writer

Help the user write a good commit message for their staged changes.

## Steps

1. Run `git diff --staged` to see what is about to be committed.
2. Identify the main purpose of the change (feature, fix, refactor, docs, test, chore).
3. Write a message in Conventional Commits format:
   - Subject line: `type(scope): summary`, imperative mood, 72 characters or fewer.
   - Blank line.
   - Optional body explaining *why* the change was made, wrapped at 80 characters.
4. Show the message to the user and ask whether they want to commit with it.
5. Only run `git commit` after the user confirms.

## Guidelines

- Do not invent changes that are not in the diff.
- If the diff mixes unrelated changes, suggest splitting it into separate commits.
- Never push to a remote unless the user explicitly asks.
