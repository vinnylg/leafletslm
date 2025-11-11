#!/bin/bash
set -e

# Carrega variáveis de ambiente
export DAGSTER_HOME="${DAGSTER_HOME:-/workspace/.dagster}"

# Cria diretórios necessários
mkdir -p "$DAGSTER_HOME/storage"

# Inicia Dagster
exec dagster dev -h 0.0.0.0 -p 3000 -w "$DAGSTER_HOME/workspace.yaml"