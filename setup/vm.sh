#!/usr/bin/env bash
# Run a command inside the Exasol Personal VM (as root). Usage: setup/vm.sh '<command>'
source "$(dirname "$0")/common.sh"
[[ -f "$RUNTIME/vm-runtime.json" ]] || die "no running Exasol Personal VM under $RUNTIME: start it (exasol start)"
IP="$(python3 -c "import json;print(json.load(open('$RUNTIME/vm-runtime.json'))['vm_ip'])")"
# Host-key checking is off on purpose: this is the local Exasol Personal VM, reached with the kit's own key, and its
# host key changes every time the VM is rebuilt. Never use these options for a remote machine.
exec ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10 -i "$RUNTIME/vm-ssh-key" "root@$IP" "$@"
