# Deployment strategy

**Status:** planned; no TransitOps service has been deployed.

## Runtime target

The working stack is intended to run on the user’s always-on VPS after Stage 1 identifies a Docker topology that fits. It is not intended to be public internet infrastructure.

Planned components:

- Reduced Airflow scheduler/API topology with LocalExecutor and low parallelism
- PostgreSQL exclusively for Airflow metadata
- Streamlit application
- Filesystem Parquet and versioned DuckDB releases
- SQLite control-plane database
- Local LanceDB index and compact embedding model

Existing unrelated containers remain outside this project’s lifecycle.

## Startup safety

The planned preflight will report resource and port conflicts and refuse unsafe startup. It will never stop other containers. Stage 1 measurements will set the memory limits.

## Application access

The operational application is intended to remain private/local or Tailscale-only. A stable private route will be selected during deployment without exposing Airflow, DuckDB, or control endpoints publicly.

## Public presentation

The required public artifact is a static branded case study at the user’s preferred portfolio route:

```text
https://ilrama.com/p/transitops-berlin
```

It will contain architecture, screenshots, a recorded demo, methodology, limitations, harness evidence, and a link to the public repository. A public live Streamlit deployment is optional and not required for project acceptance.

## Data and secret exclusions

Do not deploy or publish:

- Airflow credentials or metadata database
- `.env` values
- Unfiltered logs
- Real 14–28-day transit archives through GitHub
- Local embedding-model files or LanceDB index
- Writable operational endpoints on the public internet

## Recovery and rollback

- Failed dbt candidates leave the current DuckDB release active.
- Current and previous verified releases are retained.
- Recovery controls are allowlisted application actions only.
- Deployment rollback procedures will be written after the concrete Compose topology is verified.

## Future cloud option

Cloudflare R2 or MotherDuck may be evaluated later if measured storage or public-query needs justify them. Supabase and BigQuery are not part of version one.
