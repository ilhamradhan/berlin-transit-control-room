# Setup baseline

**Status:** design baseline; commands and exact image versions will be finalized and verified in Stage 1.

## Host constraints measured during requirements work

| Resource | Measured baseline |
|---|---:|
| CPU | 2 vCPUs |
| RAM | 3.6 GiB total |
| Swap | 1.9 GiB total |
| Root disk | 59 GB total, approximately 31 GB available at inspection |
| GPU | None |

At inspection, existing containers used approximately 597 MiB combined, the Docker daemon approximately 145 MiB, and Hermes server/gateway processes approximately 760 MiB. These values are transient measurements, not permanent requirements.

The [official Airflow Docker guide](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/) recommends at least 4 GB available to Docker and ideally 8 GB for its example stack. The host is below that recommendation. TransitOps Berlin therefore starts with a measured lightweight spike rather than copying the example Compose topology.

## Stage 1 setup goals

- Pin runtime and container versions.
- Use a slim Airflow image with only required providers.
- Use PostgreSQL for Airflow metadata.
- Use LocalExecutor with low measured parallelism.
- Run only required Airflow components.
- Apply explicit resource limits after measuring startup behavior.
- Verify one sample DAG under idle and active load.
- Run a bounded comparison of three representative stops through `v6.vbb.transport.rest`; do not crawl or archive the network.
- Fall back to Airflow standalone only if the production-shaped topology is unstable, and label standalone accurately as a learning/development deployment.

## Non-destructive preflight

The planned startup preflight reports:

- Available memory and swap pressure
- Available project disk space
- Required port conflicts
- Required directories and permissions
- Configuration presence without printing secret values

It refuses unsafe startup with actionable instructions. It never stops unrelated containers or services. The memory threshold will come from the Stage 1 spike, not an invented constant.

## Planned local directories

```text
data/
├── raw/realtime/          # 48-hour retention; ignored by Git
├── quarantine/            # invalid raw payloads; same 48-hour limit
├── parquet/observations/  # date-partitioned history; ignored by Git
├── static/active/         # extracted active GTFS; ignored by Git
└── static/archive/        # compressed versions referenced by retained observations
warehouse/
├── releases/              # current + previous DuckDB; ignored by Git
└── current.json           # runtime publication manifest; generated
state/
└── control.sqlite3        # incident control plane; ignored by Git
models/
└── embeddings/            # local model cache; ignored by Git
rag/
└── index/                 # LanceDB; ignored by Git
```

## Secrets boundary

Secrets will be supplied through ignored environment/configuration mechanisms. No secret value belongs in Git, harness records, screenshots, model context, or logs. A future `.env.example` will contain names and safe descriptions only.

## Initial verification gate

Stage 1 is accepted only when:

1. Existing services remain healthy.
2. The reduced Airflow topology starts without restart loops or unsafe swap growth.
3. A sample DAG succeeds.
4. Idle and active memory are recorded.
5. Source responses and contracts are validated from real samples.
6. The measured storage pilot procedure is ready.
