#!/usr/bin/env bash
# Polls the /health endpoint every 10s and logs the HTTP status code + UTC timestamp.
set -euo pipefail

HEALTH_URL="${HEALTH_URL:-http://localhost:5000/health}"
INTERVAL="${INTERVAL:-10}"
LOG_FILE="${LOG_FILE:-health-monitor.log}"

echo "Polling ${HEALTH_URL} every ${INTERVAL}s. Logging to ${LOG_FILE}. Press Ctrl+C to stop."

while true; do
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  # curl's %{http_code} already prints 000 on a failed connection; only fall
  # back to 000 if curl produced no output at all (avoids doubling to 000000).
  # `|| true` keeps a failed curl (unreachable host) from tripping `set -e` and
  # killing the monitor. curl's %{http_code} still prints 000 on failure.
  status_code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${HEALTH_URL}" 2>/dev/null || true)"
  [ -z "${status_code}" ] && status_code="000"

  # Translate the HTTP code into a readable status word.
  if [ "${status_code}" = "200" ]; then
    status_text="OK (healthy)"
  elif [ "${status_code}" = "000" ]; then
    status_text="NOT OK (unreachable)"
  else
    status_text="NOT OK (unhealthy)"
  fi

  line="${timestamp} | ${HEALTH_URL} | HTTP ${status_code} | ${status_text}"
  echo "${line}" | tee -a "${LOG_FILE}"
  sleep "${INTERVAL}"
done
