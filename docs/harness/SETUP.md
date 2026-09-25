# Setup baseline

**Status:** Stage 1 passed. Airflow 3.3.1 standalone was invalidated as a production service on this host; cron production-readiness checks and independent review pass.

## Host constraints measured during requirements work

| Resource | Measured baseline |
|---|---:|
| CPU | 2 vCPUs |
| RAM | 3.6 GiB total |
| Swap | 1.9 GiB total |
| Root disk | 59 GB total, approximately 31 GB available at inspection |
| GPU | None |

At inspection, existing containers used approximately 597 MiB combined, the Docker daemon approximately 145 MiB, and Hermes server/gateway processes approximately 760 MiB. These values are transient measurements, not permanent requirements.

The [official Airflow Docker guide](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/) recommends at least 4 GB available to Docker and ideally 8 GB for its example stack. The host is below that recommendation. In the corrected Airflow 3.3.1 standalone run, container memory peaked at 756 MiB and swap increased across all three 30-second samples. The safety stop fired at 60 seconds before a scheduler-executed DAG or five-minute observation completed. Existing services remained unchanged and cleanup passed, but no Airflow topology is approved for this host.

## Accepted scheduler environment

- Production collection uses the host's active cron service and `/usr/bin/python3` 3.12.3.
- Cron calls shared idempotent pipeline commands under an exclusive non-blocking lock.
- Dockerized Airflow is deferred to the Stage 2 synthetic demo and cannot access production inputs, state, or output paths.
- No Airflow image, metadata database, executor, port, or production service is required on this VPS.
- Do not retry Airflow feasibility on this VPS.

## Non-destructive preflight

The Stage 1 smoke preflight reports and checks:

- Available memory
- Available project disk space
- Exclusive-lock availability
- Response size, non-empty body, and protobuf media type

It refuses the smoke run below 512 MiB available memory, below the 4 GiB collection-cap floor, or while another run holds the lock. It never stops unrelated containers or services and prints no payload or secret value.

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
└── index/                 # local retrieval index; ignored by Git
```

## Secrets boundary

Secrets will be supplied through ignored environment/configuration mechanisms. No secret value belongs in Git, harness records, screenshots, model context, or logs. A future `.env.example` will contain names and safe descriptions only.

## Initial verification gate

Stage 1 is accepted only when:

1. Existing services remain healthy.
2. A cron-triggered real-source smoke run succeeds without overlap.
3. The smoke command remains within measured memory, swap, and disk limits.
4. Idle and active memory are recorded.
5. Source responses and contracts are validated from real samples.
6. The measured storage pilot procedure is ready.
