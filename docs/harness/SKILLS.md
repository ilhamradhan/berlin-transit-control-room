# Skill ledger

A skill is **used** only when its workflow changes an artifact or action. Reading a skill to understand it is not enough.

## Active implementation guardrail

`ponytail:ponytail` is required at `full` before planning, writing, refactoring, debugging, or reviewing code. `ponytail:ponytail-review` checks implementation diffs for avoidable complexity at coding-stage gates; it does not replace correctness, security, or acceptance review.

## Used

| Skill | Where it helped |
|---|---|
| `grill-me` | Ran the requirements interview that produced the accepted decisions. The skill delegates internally to the `grilling` workflow. |
| `github-repo-management` | Guided public repository creation and remote verification. |
| `hermes-agent` | Set up and verified the project-scoped Kanban board and durable stage dependencies. |
| `agent-harness-project-delivery` | Checked the repository's skill accounting, stage records, status labels, and publication evidence. |
| `architecture-diagram` | Produced the embedded SVG and standalone HTML target-architecture diagram. |
| `caveman-commit` | Produced the concise Conventional Commit message for the documentation correction. |
| `ponytail:ponytail` | Kept the failed Airflow runtime out of the repository and limited Stage 1 promotion to accepted aggregate evidence. |
| `ponytail:ponytail-review` | Checked the gate diff for duplicate evidence and speculative runtime artifacts. |
| `test-driven-development` | Drove failing tests before the retained smoke command and each blocking correction. |
| `requesting-code-review` | Found and verified fixes for unsafe locking, unbounded response time, non-JSON failures, unsupported evidence, test isolation, and stale architecture labels. |
| `design-taste-frontend` (design profile) | Audited the Stage 4 pages and produced `stages/05-design-brief.md` with hierarchy, responsive, accessibility, copy, and anti-slop constraints. |
| `emil-design-eng` (design profile) | Guided the restrained visual hierarchy, spacing, typography, focus, and motion-scope recommendations in `stages/05-design-brief.md`. |

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

## Stage 5 profile separation

Stage 5 separates design exploration from implementation:

- **Design profile:** audit the existing pages, propose visual direction,
  responsive behavior, information hierarchy, and user-facing copy. It may
  use Taste Skill v2, Emil's design-engineering guidance, and a content/UX
  writing skill when those are installed and explicitly selected. It does not
  edit the TransitOps worktree.
- **Code profile:** implement only the approved design/content brief in the
  existing plain HTML/CSS stack, then run tests, browser QA, accessibility,
  privacy, and complexity checks.

The design profile's output is a proposal until the user accepts it. Do not
record a design skill as used until it materially changes a reviewed brief or
artifact.

These entries are candidates or selected future tools, not work already completed.

## Excluded

- Excalidraw was considered, but the project uses a dark HTML/SVG architecture diagram.
- Autonomous multi-agent implementation is not part of the current plan.

## What to record after using a skill

Record the exact name, why it fit, the input, the artifact or action it affected, the check performed, and any deviation from the skill's normal workflow.
