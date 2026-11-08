---
name: career-ingestion
description: Ingest local career documents into the compass Obsidian data model when the user asks to organize resumes, work history, project materials, or career achievements. Do not use for job research or external application actions.
---

# Career ingestion

Use this skill to turn local career materials into structured Obsidian notes while preserving the user's facts and confidential information.

## Required context

Before writing, read the repository `AGENTS.md` and the relevant sections of `REQUIREMENTS.md`. Resolve the configured Vault and archive locations from local configuration; never hard-code a user's home directory in tracked files.

## Workflow

1. Inventory the supplied files or folders. Preserve originals in the configured local archive and do not copy them into the Vault.
2. Extract text, tables, and OCR where applicable. Keep temporary extraction output in `.runtime/` only.
3. Compare extracted facts with existing notes under the Vault's `compass/` directory.
4. Create or update career, project, achievement, and skill metadata according to the repository schemas and templates.
5. Ask immediately when sources conflict on dates, roles, numeric outcomes, or when a detail could be confidential outside the user's employer.
6. Validate the affected notes and links. On a critical failure, restore the pre-operation snapshot.
7. Report the notes changed and the questions that remain.

## Data rules

- A career note represents a tenure at one employer and employment type. Record role changes within the same note.
- A project may represent product development, operations, technical improvement, hiring, management, OSS, speaking, or writing when it is useful in a career narrative.
- An achievement is a reusable, material outcome linked to a project. Record context, the user's role, actions, and outcome; quantified results are preferred but not required.
- Store skills as Frontmatter lists on relevant notes rather than creating one note per skill.
- Source links for career facts are optional. Do not invent them merely to satisfy a template.

## Safety rules

- Do not turn uncertain OCR or inference into a confirmed fact.
- Do not move client names, internal URLs, credentials, or non-public metrics into application-facing prose without asking the user.
- Do not modify a user's own notes outside `compass/` unless explicitly directed.
