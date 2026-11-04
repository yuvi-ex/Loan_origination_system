#!/usr/bin/env bash
# Start the LOS service (127.0.0.1:LOS_PORT from config.env) in the background unless it already answers.
# Log: .work/los_api.log. Stop it: pkill -f "$PWD/service/los_api.py"
source "$(dirname "$0")/../setup/common.sh"
URL="http://127.0.0.1:$LOS_PORT"
curl -sf -m 2 "$URL/health" >/dev/null && { echo "LOS service already running on $URL"; exit 0; }
nohup "$PY" "$ROOT/service/los_api.py" >>"$WORK/los_api.log" 2>&1 &
for _ in $(seq 1 30); do curl -sf -m 1 "$URL/health" >/dev/null && { echo "LOS service started on $URL"; exit 0; }; sleep 0.5; done
echo "LOS service did not start. Last lines of $WORK/los_api.log:" >&2; tail -5 "$WORK/los_api.log" >&2; exit 1
