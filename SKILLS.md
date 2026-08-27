# Skill Usage

## Status definitions

- **Used:** the skill workflow materially guided a project artifact or action.
- **Selected for later:** accepted as a likely phase tool but not yet used to produce that phase’s artifact.
- **Candidate:** may fit, but requires confirmation at the relevant phase.
- **Inspected only:** loaded to understand its behavior; not credited as producing project work.

## Used so far

| Skill | Status | Contribution |
|---|---|---|
| `grill-me` → `grilling` | Used | Drove the requirements interview and decision tree summarized in the foundational documents. |
| `github-repo-management` | Used | Guided authenticated creation and verification of the public GitHub repository. |

The initial requirements process used only `grill-me`/`grilling` as its project-design skill. Tool-based research and system measurements are evidence, not skills.

## Selected phase map

| Trigger or phase | Suggested skill | Current status | Intended result |
|---|---|---|---|
| Requirements remain ambiguous | `grill-me` / `grilling` | Used | Resolved decision record |
| Domain terms or boundaries need sharpening | `domain-modeling` | Candidate | Domain glossary and invariants |
| A stage needs an actionable implementation plan | `plan` | Selected for later | Plan artifact before execution |
| New production behavior is implemented | `test-driven-development` | Selected for later | Red–green–refactor evidence |
| A failure has an unknown cause | `systematic-debugging` | Selected for later | Root-cause record before correction |
| A stage appears complete | `requesting-code-review` | Selected for later | Independent stage-gate review |
| Runnable user journeys need exploratory QA | `dogfood` | Selected for later | Browser evidence and issue report |
| Portfolio architecture needs a dark diagram | `architecture-diagram` | Selected for later | Standalone dark HTML/SVG diagram |
| Hermes configuration itself is changed | `hermes-agent` | Candidate | Current documented Hermes procedure |

## Explicit exclusions and corrections

- `streamlit-analytics-dashboard-redesign` is **not** part of this project’s skill chain.
- `excalidraw` is not the required architecture format; the selected output is the dark HTML/SVG `architecture-diagram` workflow.
- Loading a skill for inspection does not make it “used.”
- Autonomous multi-agent implementation is not part of the accepted baseline.

## Per-stage recording template

For every skill actually used, record:

- Exact skill name
- Why it fit the phase
- Inputs supplied
- Outputs produced
- Verification performed
- Required or optional status
- Deviations from its standard workflow
