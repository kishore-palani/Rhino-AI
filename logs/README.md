# AI RHINO ARCHITECT — Project Log System

This folder is the **central memory and audit trail** for the AI RHINO ARCHITECT
project. Every AI session, code change, decision, and milestone is logged here so
that any AI agent (current or future) can read it to understand the full project
history and continue work without context loss.

## Structure

```
logs/
├── README.md                 ← This file
├── SESSION_INDEX.md          ← Master index of every session (newest first)
├── CHANGELOG.md              ← Running record of all code/file changes
├── DECISIONS.md              ← Architectural and design decisions log
├── PROJECT_STATE.md          ← Current snapshot of project state (updated each session)
├── ISSUES.md                 ← Known issues, bugs, and blockers
├── sessions/                 ← One file per session with full details
│   └── YYYY-MM-DD_NNN.md    ← Individual session log
└── milestones/               ← Milestone completion records
    └── phase-N-complete.md   ← Phase completion snapshots
```

## How It Works

### For AI Agents

1. **Start of session:** Read `PROJECT_STATE.md` to know where things stand.
2. **During work:** Record changes in the session log and `CHANGELOG.md`.
3. **End of session:** Update `PROJECT_STATE.md`, add session to `SESSION_INDEX.md`.

### For Humans

Browse `SESSION_INDEX.md` for a quick history, or drill into `sessions/` for
full detail on what happened in any particular work session.

## File Contracts

| File               | Updated when…                         |
|--------------------|---------------------------------------|
| `SESSION_INDEX.md` | Every session (append one line)       |
| `CHANGELOG.md`     | Any file is created, modified, deleted|
| `DECISIONS.md`     | An architectural or design choice is made |
| `PROJECT_STATE.md` | Every session end                     |
| `ISSUES.md`        | A bug/issue is found or resolved      |

## Naming Convention

Session files: `YYYY-MM-DD_NNN.md` where NNN is a zero-padded sequence number
for that day (001, 002, …).
