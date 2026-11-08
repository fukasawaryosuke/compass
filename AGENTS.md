# Codex project instructions

## Before making changes

- Inspect the repository and its existing documentation before choosing tools or conventions.
- Follow the project's established language, formatting, and architecture choices.
- If the repository is empty or a decision would materially shape the project, ask the user before introducing a framework or runtime.

## While working

- Keep changes focused on the requested task.
- Explain assumptions when requirements are unclear, and prefer the smallest reasonable implementation.
- Do not add dependencies, tests, or generated files unless the task needs them or the user asks.
- Never expose credentials, tokens, or other secrets in output or committed files.

## Before finishing

- Summarize the files changed and any decisions that need the user's input.
- Report checks that were run and their results. Do not claim checks passed if they were not run.
