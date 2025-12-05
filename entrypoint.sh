#!/bin/bash
set -e
make dev
make test-env
exec "$@"
