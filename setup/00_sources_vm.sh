#!/usr/bin/env bash
# Start the lender's three outside systems in podman INSIDE the Exasol Personal VM. Idempotent; re-run after the VM
# restarts (preflight does).
#   los-core-pg      Postgres 16       core banking: customers, accounts, transactions        VM port $PG_PORT
#   los-docs-mongo   MongoDB 8.2       loan applications + what was read off each PDF          VM port $MONGO_PORT
#   los-bureau-api   Python 3.12       the credit bureau's REST API, mocked (data/bureau_api.py) VM port $BUREAU_PORT
# Why inside the VM: the database runs in that VM, so it reaches the containers through the podman gateway (SRC_HOST),
# and nothing depends on the host's firewall letting the VM in. The VM has no internet: images are pulled on the host
# with Docker (or podman) once and streamed in.
source "$(dirname "$0")/common.sh"
VM="$ROOT/setup/vm.sh"
ENGINE=""      # the first container engine that is installed AND running (Docker Desktop may be installed but stopped)
for e in docker podman; do command -v "$e" >/dev/null && "$e" info >/dev/null 2>&1 && { ENGINE=$e; break; }; done

say "1. Images in the VM"
for img in postgres:16 mongo:8.2 python:3.12-slim; do      # NOT mongo 8.0/latest: no boot on kernels >= 6.19
  if ! "$VM" "podman image exists localhost/$img"; then
    [[ -n "$ENGINE" ]] || die "$img must be fetched on this machine: start Docker Desktop (or podman), then run setup/install.sh --from sources"
    "$ENGINE" pull -q "docker.io/library/$img" >/dev/null
    "$ENGINE" save "docker.io/library/$img" | "$VM" 'podman load' | tail -1 | sed 's/^/    /'
    "$VM" "podman image exists localhost/$img || podman tag docker.io/library/$img localhost/$img"
  fi
done
ok "postgres:16, mongo:8.2, python:3.12-slim"

say "2. Containers"
# Admin passwords come from secrets/sources.env (setup/common.sh generates them). The ports are published inside the
# Exasol Personal VM, whose network is host-only: reachable from this machine and the database, not from the LAN.
mkdir -p "$BUREAU_DIR"
"$VM" "
podman volume exists los-core || podman volume create los-core >/dev/null
podman volume exists los-docs || podman volume create los-docs >/dev/null
podman container exists los-core-pg || podman create --name los-core-pg --restart always \
  -e POSTGRES_USER=cbs_admin -e POSTGRES_PASSWORD=$PG_ADMIN_PASSWORD -e POSTGRES_DB=core_banking \
  -p $PG_PORT:5432 -v los-core:/var/lib/postgresql/data localhost/postgres:16 >/dev/null
podman container exists los-docs-mongo || podman create --name los-docs-mongo --restart always \
  -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=$MONGO_ROOT_PASSWORD \
  -p $MONGO_PORT:27017 -v los-docs:/data/db localhost/mongo:8.2 --wiredTigerCacheSizeGB 0.5 >/dev/null
podman container exists los-bureau-api || podman create --name los-bureau-api --restart always \
  -p $BUREAU_PORT:8000 -v /mnt/host/los-bureau-api:/srv:ro localhost/python:3.12-slim python -u /srv/api.py >/dev/null
podman start los-core-pg los-docs-mongo >/dev/null
[ -f /mnt/host/los-bureau-api/api.py ] && podman start los-bureau-api >/dev/null || true
podman ps --filter name=los- --format '{{.Names}}  {{.Status}}  {{.Ports}}'" | sed 's/^/    /'
