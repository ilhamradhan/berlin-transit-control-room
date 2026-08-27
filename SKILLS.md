# Skill ledger

A skill is **used** only when its workflow changes an artifact or action. Reading a skill to understand it is not enough.

## Used

| Skill | Where it helped |
|---|---|
| `grill-me` | Ran the requirements interview that produced the accepted decisions. The skill delegates internally to the `grilling` workflow. |
| `github-repo-management` | Guided public repository creation and remote verification. |
| `humanizer` | Guided the anti-slop documentation pass after the initial baseline. |
| `agent-harness-project-delivery` | Checked the repository's skill accounting, stage records, status labels, and publication evidence. |
| `caveman-commit` | Produced the concise Conventional Commit message for the documentation correction. |

There is no installed `/unslop` skill. `humanizer` is the matching installed workflow.

`requesting-code-review` was inspected but not used because its own workflow says to skip documentation-only changes.

## Likely later

| When it fits | Skill | Expected output |
|---|---|---|
| Domain terms are still unclear | `domain-modeling` | Glossary and invariants |
| A stage is ready to break into tasks | `plan` | Executable stage plan |
| New code behavior starts | `test-driven-development` | Failing test, minimal fix, passing test |
| A failure has no known cause | `systematic-debugging` | Reproduction and root-cause record |
| A stage appears complete | `requesting-code-review` | Independent gate review |
| The app can be used in a browser | `dogfood` | Exploratory QA report |
| The case study needs its system diagram | `architecture-diagram` | Dark HTML/SVG diagram |
| Hermes configuration itself changes | `hermes-agent` | Verified Hermes procedure |

These entries are candidates or selected future tools, not work already completed.

## Excluded

- `streamlit-analytics-dashboard-redesign` is not part of this project.
- Excalidraw was considered, but the selected diagram format is the dark HTML/SVG `architecture-diagram` workflow.
- Autonomous multi-agent implementation is not part of the current plan.

## What to record after using a skill

Record the exact name, why it fit, the input, the artifact or action it affected, the check performed, and any deviation from the skill's normal workflow.
