# Harness documentation

This folder contains the project design, agent instructions, stage gates, and evidence records. The implementation has not started. The completed work is the design baseline in [`stages/00-design-baseline.md`](stages/00-design-baseline.md).

## Start here

| Document | Purpose |
|---|---|
| [`CONTINUE.md`](CONTINUE.md) | Copy-paste prompts for starting or resuming work |
| [`PROMPT.md`](PROMPT.md) | Accepted project brief and ownership statement |
| [`PLAN.md`](PLAN.md) | Six implementation stages and their gates |
| [`HARNESS.md`](HARNESS.md) | Rules for agent use, evidence, and stage completion |
| [`EVALUATION.md`](EVALUATION.md) | Checks that prove a stage is complete |
| [`SKILLS.md`](SKILLS.md) | Skills used, proposed, inspected, or excluded |

## Design and operations

| Document | Purpose |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Planned components, boundaries, and data flow |
| [`DECISIONS.md`](DECISIONS.md) | Accepted choices and rejected alternatives |
| [`SETUP.md`](SETUP.md) | VPS constraints and setup checks |
| [`DEPLOY.md`](DEPLOY.md) | Planned private runtime and public case study |
| [`RUNBOOKS.md`](RUNBOOKS.md) | Planned incident procedures |

## Stage workflow

1. Read the current stage in [`PLAN.md`](PLAN.md) and its checks in [`EVALUATION.md`](EVALUATION.md).
2. Use the matching prompt in [`CONTINUE.md`](CONTINUE.md).
3. Approve the stage plan before implementation starts.
4. Work on one stage only. Record real commands, results, deviations, and skills that changed the work.
5. Run the gate checks and update the stage record.
6. Start the next stage only after the current gate passes.

Stage records live in [`stages/`](stages/). They are curated evidence, not raw chat transcripts.
