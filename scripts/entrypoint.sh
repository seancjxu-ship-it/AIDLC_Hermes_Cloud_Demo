#!/bin/sh
set -eu

case "${1:-api}" in
  api)
    exec uvicorn aidlc.api:app --host 0.0.0.0 --port 8000
    ;;
  orchestrator)
    exec python -m aidlc.orchestrator_main
    ;;
  worker)
    exec python -m aidlc.worker_main "${2:?worker role is required}"
    ;;
  *)
    exec "$@"
    ;;
esac

