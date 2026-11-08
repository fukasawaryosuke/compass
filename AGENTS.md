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

## compass agent contract

Read `REQUIREMENTS.md` before changing the compass data model, templates, agent workflows, or any code that writes to the Obsidian Vault.

### Boundaries

- This repository contains the harness. It must not contain personal career data, job postings, credentials, browser cookies, OCR output, or generated application documents.
- The managed Vault is configured locally and is not Git-managed. Agents may read and write only its `compass/` directory unless the user explicitly names another note or directory.
- Local runtime state belongs under `.runtime/` and must stay untracked. Preserve only the minimum data needed for execution logs, caches, locks, and 30-day rollback snapshots.
- Original documents and exported PDF/Word files live in the local archive, not in the Vault or repository.

### Writing managed data

- For clear, non-conflicting facts, update the appropriate approved Vault note automatically.
- Ask the user before deciding between conflicting source facts, filling material gaps, or reusing potentially confidential information.
- Never delete or substantially rewrite user-authored prose without an explicit request.
- Do not persist temporary drafts after a successful, validated promotion. Keep unresolved drafts until they are resolved.
- Validate Frontmatter, Markdown structure, links, and duplicate candidates after each write. Roll back the current operation when a critical validation fails.

### External services

- Read public web pages when needed for an explicitly requested company or job investigation.
- A logged-in browser session may be read only when the user requests that operation. Never store or expose credentials, cookies, or MFA codes.
- Never submit an application, send a message, reply to a scout, schedule a meeting, or otherwise mutate an external service. Produce drafts only when requested.

### Working style

- Treat the user's explicit interest or rejection of a company as authoritative over an AI-generated score.
- Keep company and job research dated and linked to its public source URLs. Do not save complete web-page copies.
- Report changed Vault notes and unresolved questions concisely after a successful operation.
- Use a single-writer lock for a Vault operation to avoid iCloud synchronization conflicts.
