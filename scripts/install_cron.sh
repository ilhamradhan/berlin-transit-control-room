#!/usr/bin/env bash
set -euo pipefail

repo=""
input=""
dry_run=0
while (($#)); do
  case "$1" in
    --repo) repo=$2; shift 2 ;;
    --input) input=$2; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ -z "$repo" ]]; then
  printf '%s\n' '--repo is required' >&2
  exit 2
fi
repo=$(cd "$repo" && pwd -P)
repo_q=$(printf '%q' "$repo")
campaign_start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [[ -n "$input" ]]; then
  current=$(<"$input")
else
  current=$(crontab -l 2>/dev/null || true)
fi

block=$(cat <<EOF
# BEGIN TRANSITOPS BERLIN
*/15 * * * * cd $repo_q && mkdir -p state && flock -n state/realtime.lock .venv/bin/python scripts/transitops.py realtime --runtime-root $repo_q --root data --state-root state --namespace production --scheduler cron --data-origin real --campaign-start $campaign_start --realtime-url https://production.gtfsrt.vbb.de/data --slot-now
7 2 * * * cd $repo_q && mkdir -p state && flock -n state/static.lock .venv/bin/python scripts/transitops.py static --runtime-root $repo_q --root data --state-root state --namespace production --scheduler cron --data-origin real --campaign-start $campaign_start --static-url https://unternehmen.vbb.de/gtfs
22 2 * * * cd $repo_q && mkdir -p state && flock -n state/maintain.lock .venv/bin/python scripts/transitops.py maintain --runtime-root $repo_q --root data --state-root state --namespace production --scheduler cron --data-origin real --campaign-start $campaign_start
# END TRANSITOPS BERLIN
EOF
)

if ! printf '%s\n' "$current" | awk '
  /# BEGIN TRANSITOPS BERLIN$/ {if (inside) {bad=1}; inside=1; begins++}
  /# END TRANSITOPS BERLIN$/ {if (!inside) {bad=1}; inside=0; ends++}
  END {if (inside || begins != ends) {bad=1}; exit bad}
'; then
  printf '%s\n' 'malformed TransitOps crontab markers; refusing to modify crontab' >&2
  exit 1
fi

stripped=$(printf '%s\n' "$current" | awk '
  /^# BEGIN TRANSITOPS BERLIN$/ {skip=1; next}
  /^# END TRANSITOPS BERLIN$/ {skip=0; next}
  !skip {print}
')
updated=$(printf '%s\n%s\n' "$stripped" "$block")
printf '%s\n' "$updated"

if (( !dry_run )); then
  printf '%s\n' "$updated" | crontab -
fi
