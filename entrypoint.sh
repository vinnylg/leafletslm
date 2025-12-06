#!/bin/bash
set -e

LOCK=".entrypoint.lock"

echo ">>> [entrypoint] Attempting to acquire lock..."

(
    flock -n 9 \
        && echo ">>> [entrypoint] Lock acquired. Running make dev..." \
        && make dev \
        || echo ">>> [entrypoint] Lock held by another container. Skipping make dev."
) 9>"$LOCK"

echo ">>> [entrypoint] Executing main command: $@"
exec "$@"

