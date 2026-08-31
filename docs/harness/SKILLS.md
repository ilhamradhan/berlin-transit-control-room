# Skill ledger

A skill is **used** only when its workflow changes an artifact or action. Reading a skill to understand it is not enough.

## Active implementation guardrail

`ponytail:ponytail` is active at `full`. It must be loaded before planning, writing, refactoring, debugging, or reviewing code from Stage 1 onward. The project context file [`.hermes.md`](../../.hermes.md) enforces this in future Hermes sessions. `ponytail:ponytail-review` checks implementation diffs for avoidable complexity at coding-stage gates; it does not replace correctness, security, or acceptance review.

## Used

| Skill | Where it helped |
|---|---|
| `grill-me` | Ran the requirements interview that produced the accepted decisions. The skill delegates internally to the `grilling` workflow. |
| `github-repo-management` | Guided public repository creation and remote verification. |
| `hermes-agent` | Set up and verified the project-scoped Kanban board and durable stage dependencies. |
| `agent-harness-project-delivery` | Checked the repository's skill accounting, stage records, status labels, and publication evidence. |
| `architecture-diagram` | Produced the embedded SVG and standalone HTML target-architecture diagram. |
| `caveman-commit` | Produced the concise Conventional Commit message for the documentation correction. |

`requesting-code-review` was inspected but not used because its own workflow says to skip documentation-only changes.

## Likely later

| When it fits | Skill | Expected output |
|---|---|---|
| Domain terms are still unclear | `domain-modeling` | Glossary and invariants |
| A stage is ready to break into tasks | `plan` | Executable stage plan |
| A feasibility question needs measured evidence | `spike` | Disposable experiment and verdict |
| New code behavior starts | `test-driven-development` | Failing test, minimal fix, passing test |
| A failure has no known cause | `systematic-debugging` | Reproduction and root-cause record |
| A stage appears complete | `requesting-code-review` | Independent gate review |
| The app can be used in a browser | `dogfood` | Exploratory QA report |
| Hermes configuration itself changes | `hermes-agent` | Verified Hermes procedure |

These entries are candidates or selected future tools, not work already completed.

## Excluded

- `streamlit-analytics-dashboard-redesign` is not part of this project.
- Excalidraw was considered, but the project uses a dark HTML/SVG architecture diagram.
- Autonomous multi-agent implementation is not part of the current plan.

## What to record after using a skill

Record the exact name, why it fit, the input, the artifact or action it affected, the check performed, and any deviation from the skill's normal workflow.
