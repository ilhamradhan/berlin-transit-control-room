# Harness

This project documents two kinds of control:

- The **agent harness** defines the prompt, context, constraints, skill choice, phase gates, and evidence expected from Hermes.
- The **delivery harness** defines the environment, tests, orchestration, retention, deployment, and recovery rules for the data system.

I own the product choices and acceptance criteria. Agent output counts only after a check shows that it works.

## Delivery stages

| Stage | Output | Proof needed to pass |
|---|---|---|
| 1. Setup and source validation | Resource-safe skeleton, source samples, contracts, architecture | Measured resource use, valid samples, successful test DAG |
| 2. Ingestion and storage | Scheduled collection, retention, Parquet compaction | Tests, successful DAG run, storage projection |
| 3. Transformation and quality | dbt models, tests, versioned DuckDB publication | dbt artifacts and publication checks |
| 4. Control Room | Health views, incidents, three demo controls | Browser checks and incident audit records |
| 5. RAG assistant | Sanitized corpus and cited answers | Retrieval, citation, refusal, and leakage tests |
| 6. Portfolio presentation | Reliability explorer, diagram, case study, demo | Browser QA and published artifacts |

Writing files does not pass a stage. The checks in [`EVALUATION.md`](EVALUATION.md) do.

## Stage records

Each file in `docs/harness/stages/` records:

1. my request;
2. the self-contained prompt Hermes used, embedded or linked at the same Git commit;
3. assumptions and constraints;
4. skills that materially guided the work;
5. acceptance criteria;
6. a short execution summary;
7. commands and relevant output;
8. deviations and lessons.

Raw transcripts, chain-of-thought, secrets, and unfiltered logs do not belong in the repository.

Hermes Kanban board `transitops-berlin` tracks active local work and stage dependencies. Kanban state is coordination data, not portfolio evidence; the curated stage records remain the public source of accepted prompts, checks, results, and deviations.

## Working rules

- Mark unbuilt features as planned.
- Load `ponytail:ponytail` at `full` before any coding task and keep it active until the user explicitly disables it.
- Use the smallest skill set that fits the current stage.
- Do not call a skill "used" merely because it was inspected.
- Test new behavior before accepting it.
- Test DuckDB candidates before changing the current-release manifest.
- Read back remote writes before reporting success.
- Do not send secrets, connection strings, environment variables, or raw logs to Gemini.
- Do not let the LLM run commands or change pipeline state.
- Do not stop unrelated VPS services.
- Before a coding stage passes, run the normal acceptance checks and a separate `ponytail:ponytail-review`; complexity review never replaces correctness review.

## Choosing skills

Before a stage, identify the actual uncertainty and suggest one matching skill. Load it only when its workflow will guide the work, then record what it produced and how that output was checked. [`SKILLS.md`](SKILLS.md) tracks the current choices.
