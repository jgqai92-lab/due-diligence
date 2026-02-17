# Financial Due Diligence Application -- Claude Code Instructions

Read `context.md` first for project orientation.

## Workflow
- **Framework:** SDE (Strategic Development Engine)
- **Rules:** `~/.claude/SDE_WORKFLOW.md`
- **Commander:** @orchestrator

## Critical Files
- `context.md` -- shared project context (update at phase transitions)
- `.claude/PROGRESS.md` -- phase tracking and checkpoint log
- `spec/` -- specification templates (filled by agents)
- `.project-manifest.json` -- scaffolding manifest

## Phase Transition Protocol
When a phase completes, update `context.md`:
1. Set **Current Phase** and **Status** in the Project Identity table
2. Append a row to the Phase History table
3. Log any key decisions made during the phase

## Boundaries
- Do NOT modify `AGENTS.md` (Codex instructions)
