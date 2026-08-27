# Harness Engineering

## Purpose

The harness makes agent-assisted development reproducible and reviewable. It has two connected parts:

- **Agent harness:** prompts, context, phase skills, constraints, tool boundaries, acceptance criteria, and verification evidence.
- **Delivery harness:** reproducible setup, orchestration, tests, observability, retention, deployment controls, and recovery procedures.

The agent may assist with research, planning, implementation, documentation, and verification. The user owns product and architecture decisions. A phase completes only when its acceptance criteria are supported by real evidence.

## Phase-gated lifecycle

| Gate | Required output | Evidence required |
|---|---|---|
| 1. Setup and source validation | Resource-safe skeleton, source samples, contracts, architecture | Commands and measured results |
| 2. Ingestion and storage | Scheduled collection, retention, Parquet compaction | Tests, sample DAG run, storage projection |
| 3. Transformation and quality | dbt layers, metrics, versioned DuckDB publication | dbt artifacts, tests, release verification |
| 4. Control Room | Health views, incidents, three deterministic recoveries | Browser checks and incident audit records |
| 5. RAG assistant | Sanitized corpus, retrieval, cited read-only answers | Formal retrieval and answer evaluation |
| 6. Portfolio presentation | Reliability explorer, diagram, case study, demo | Browser QA and published/recorded artifacts |

A runnable verified increment is required before advancing.

## Stage record contract

Each `docs/harness/stages/*.md` record contains:

1. User intent
2. Rephrased execution prompt
3. Assumptions and constraints
4. Skills actually used and why
5. Acceptance criteria
6. Execution summary
7. Verification evidence with real results
8. Deviations
9. Lessons learned

Skills discussed or loaded for inspection are not described as having produced an artifact. Planned skills remain clearly labeled until used.

## Agent boundaries

- Do not expose or commit secrets.
- Do not send secrets, environment variables, connection strings, or unfiltered logs to Gemini.
- Do not allow the LLM to execute commands or alter pipeline state.
- Do not accept shell commands from dashboard users or the LLM.
- Do not stop or modify unrelated VPS services.
- Do not publish real collected datasets in Git.
- Do not advance a phase based solely on plausible-looking code.

## Verification discipline

- Reproduce a bug before fixing it when practical.
- Use failing tests before new production behavior when appropriate.
- Test candidate DuckDB releases before publication.
- Read back external writes before claiming success.
- Record actual commands and concise relevant output, never fabricated output.
- Mark design-only artifacts as planned rather than implemented.

## Skill selection rule

Use the smallest phase-specific skill set. Before each phase:

1. Identify the phase goal and uncertainty.
2. Suggest the matching installed skill briefly.
3. Load the skill only when its workflow will be used.
4. Record it as “used” only when it materially guided an artifact or action.
5. Record deviations and verification.

See [`SKILLS.md`](SKILLS.md).
