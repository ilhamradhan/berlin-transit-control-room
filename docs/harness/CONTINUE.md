# Continue TransitOps Berlin

Use these prompts from the repository root. Hermes should inspect the live working tree and evidence rather than assume that a previous session finished its work.

## Short prompt

Use this when the current stage is already clear:

> Continue TransitOps Berlin from the current stage. Read `docs/harness/CONTINUE.md`, inspect the repository, the current stage record, and the local `transitops-berlin` Kanban board, then follow the resume workflow. Do not skip the stage gate. Do not commit or push unless I explicitly ask.

## Start Stage 1

> Start Stage 1 of TransitOps Berlin. Work only on the harness and source-validation stage.
>
> First read `README.md`, `docs/harness/README.md`, `docs/harness/PROMPT.md`, `docs/harness/PLAN.md`, `docs/harness/HARNESS.md`, `docs/harness/ARCHITECTURE.md`, `docs/harness/DECISIONS.md`, `docs/harness/EVALUATION.md`, `docs/harness/SETUP.md`, `docs/harness/SKILLS.md`, and `docs/harness/stages/00-design-baseline.md`. Inspect the live Git state and VPS state. Do not assume the documentation describes implemented software.
>
> Load `ponytail:ponytail` at `full` before planning or writing code. Then load `plan` and write a Stage 1 execution plan under `.hermes/plans/`. Use `spike` for the measured lightweight Airflow experiment. Suggest `domain-modeling` only if GTFS terms or source contracts remain unclear. Use `architecture-diagram` only after the measured topology is accepted.
>
> The Stage 1 plan must cover the pinned environment proposal, non-destructive preflight, VBB static and realtime sample validation, VBB feed-status evidence, the bounded `v6.vbb.transport.rest` comparison, source contracts, domain glossary, sample DAG, Airflow memory and disk measurements, architecture diagram, tests, and the Stage 1 record. Include exact files, commands, expected evidence, stop conditions, and rollback or cleanup for each disposable spike.
>
> Stop after writing and reviewing the plan. Ask for my approval before implementation. Do not commit or push unless I explicitly ask.

## Resume an interrupted stage

Replace `[N]` with the current stage number:

> Resume Stage [N] of TransitOps Berlin. Read `docs/harness/README.md`, `docs/harness/PLAN.md`, `docs/harness/HARNESS.md`, `docs/harness/EVALUATION.md`, `docs/harness/SKILLS.md`, the latest Stage [N] record, and any saved plan under `.hermes/plans/`.
>
> Inspect the live Git working tree, relevant files, running processes, and recorded evidence. Do not infer completion from a checklist or earlier message. Report four things before changing files: verified completed work, unverified claims, remaining gate criteria, and the next smallest task.
>
> Load `ponytail:ponytail` at `full` before any coding task. Continue only the next incomplete task in Stage [N]. Use the smallest matching skill set and record a skill as used only if it changes an artifact or action. Run the task's verification, update the stage record with concise evidence, and stop if a decision or unsafe side effect needs my input. Do not start Stage [N+1]. Do not commit or push unless I explicitly ask.

## Check whether a stage is complete

> Audit Stage [N] of TransitOps Berlin against its gate in `docs/harness/PLAN.md` and `docs/harness/EVALUATION.md`. Inspect and run the real checks. Update the Stage [N] record with evidence, failures, and deviations. Do not repair unrelated problems, advance to the next stage, commit, or push unless I explicitly ask.

## After a stage passes

Start the next stage in a new prompt. Name the stage explicitly and use the same pattern as the Stage 1 prompt: read the accepted records, inspect live state, create or review the stage plan, wait for approval, implement one stage, and prove the gate.
