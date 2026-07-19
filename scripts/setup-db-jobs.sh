#!/usr/bin/env bash
# Create Cloud Scheduler jobs for hourly backup + midnight reset (Europe/London).
# Prerequisites:
#   - gcloud authenticated
#   - ADMIN_TOKEN set in the environment (same value configured on Cloud Run)
#   - Cloud Run services already deployed
#
# Usage:
#   export ADMIN_TOKEN='your-token'
#   export PROJECT_ID='your-gcp-project'
#   bash scripts/setup-db-jobs.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-europe-west1}"
TIME_ZONE="${TIME_ZONE:-Europe/London}"
ADMIN_TOKEN="${ADMIN_TOKEN:?Set ADMIN_TOKEN to the same value used by Cloud Run}"

DEV_URL="${DEV_URL:-https://hello-world-dev-859465631308.europe-west1.run.app}"
PROD_URL="${PROD_URL:-https://hello-world-859465631308.europe-west1.run.app}"

create_or_update_job() {
  local name="$1"
  local schedule="$2"
  local url="$3"

  if gcloud scheduler jobs describe "$name" --location="$REGION" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "$name" \
      --location="$REGION" \
      --schedule="$schedule" \
      --time-zone="$TIME_ZONE" \
      --uri="$url" \
      --http-method=POST \
      --headers="X-Admin-Token=${ADMIN_TOKEN},Content-Type=application/json" \
      --message-body="{}"
  else
    gcloud scheduler jobs create http "$name" \
      --location="$REGION" \
      --schedule="$schedule" \
      --time-zone="$TIME_ZONE" \
      --uri="$url" \
      --http-method=POST \
      --headers="X-Admin-Token=${ADMIN_TOKEN},Content-Type=application/json" \
      --message-body="{}"
  fi
}

echo "Using project ${PROJECT_ID}, region ${REGION}, tz ${TIME_ZONE}"

create_or_update_job "hello-world-dev-hourly-backup" "0 * * * *" "${DEV_URL}/internal/db/backup"
create_or_update_job "hello-world-dev-midnight-reset" "0 0 * * *" "${DEV_URL}/internal/db/reset-to-safe"
create_or_update_job "hello-world-prod-hourly-backup" "0 * * * *" "${PROD_URL}/internal/db/backup"
create_or_update_job "hello-world-prod-midnight-reset" "0 0 * * *" "${PROD_URL}/internal/db/reset-to-safe"

echo "Scheduler jobs created/updated."
echo "Ensure Cloud Run services have ADMIN_TOKEN set to the same value."
