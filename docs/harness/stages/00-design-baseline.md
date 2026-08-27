# Baseline record: project design and repository

## My intent

Build a learning project that combines Airflow, dbt, DuckDB, and a useful AI feature. The repository should also show how I direct an AI agent: my decisions, its rephrased prompts, the skills used, and the evidence collected at each stage.

## Agent prompt

[`PROMPT.md`](../../../PROMPT.md) contains the reusable prompt produced from the requirements interview.

## Constraints accepted here

- Public code and documentation; no real archive or secrets in Git.
- Always-on VPS with 2 vCPUs, 3.6 GiB RAM, and no GPU.
- The project cannot stop or reconfigure unrelated services.
- Local storage first; revisit cloud storage only after measurement.
- Realtime collection every 15 minutes, with a 14-day minimum and a 28-day or 4 GB hard stop.
- Finish the documentation baseline before implementation.

## Skills used

| Skill | Work affected |
|---|---|
| `grill-me` | Requirements and decisions; it delegates internally to `grilling` |
| `github-repo-management` | Repository creation and read-back checks |
| `humanizer` | Documentation cleanup after the first commit |
| `agent-harness-project-delivery` | Harness-record and publication audit |
| `caveman-commit` | Commit-message format for the correction |

## Baseline acceptance criteria

- The documents separate plans from completed work.
- The reusable prompt reflects the decisions made during the interview.
- Ignore rules cover secrets, datasets, databases, models, and generated indexes.
- GitHub is public, uses `main`, and contains the same baseline commit as the local repository.

## Work completed

- Created the Hermes project at `/home/rama/project/berlin-transit-control-room`.
- Documented the requirements and accepted decisions.
- Initialized Git and published the repository.
- Checked relative links and representative ignore rules.
- Read back repository visibility, default branch, topics, and README through GitHub.
- Reworked the initial documentation to remove repeated and formulaic prose.

## Evidence

Measurements taken during the design work:

```text
Host RAM: 3.6 GiB total
Host disk: 59 GB total; about 31 GB available at inspection
Running containers: about 597 MiB combined at inspection
Hermes server and gateway: about 760 MiB combined at inspection
```

Initial repository checks:

```text
Initial commit: dff5eef
Default branch: main
Remote visibility: PUBLIC
Broken relative Markdown links: 0
```

No Airflow, dbt, DuckDB, Streamlit, or RAG code has been built or tested.

## Corrections made after the first commit

- Renamed this file from a Stage 1 record to a design baseline. Stage 1 has not started.
- Removed the dashboard-specific skill from the project plan.
- Kept the selected dark HTML/SVG diagram instead of Excalidraw.
- Separated skills used from skills merely inspected or proposed.
- Replaced the generated-sounding README with a direct first-person account of the learning project.

## What I learned from the baseline

A skill name in context does not prove it guided the work. Storage estimates also need representative payloads; the temporary 15-byte VBB realtime response was not a useful normal-case sample. Docker image size, container RAM, and host available memory are separate constraints.
