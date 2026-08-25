#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
CORE_VERSION="${CORE_VERSION:-0.6.3}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_ROOT="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_ROOT/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_ROOT"
fi

"$VENV_PYTHON" "$REPO_ROOT/scripts/repair_pip_residue.py"
"$VENV_PYTHON" -m ensurepip --upgrade

CORE_NAME="pds_core-${CORE_VERSION}-py3-none-any.whl"
CORE_WHEEL="${TMPDIR:-/tmp}/${CORE_NAME}"
CORE_URI="https://github.com/Paper-Data-Suite/pds-core/releases/download/v${CORE_VERSION}/${CORE_NAME}"

curl -fL -o "$CORE_WHEEL" "$CORE_URI"
"$VENV_PYTHON" "$REPO_ROOT/scripts/verify_core_wheel.py" "$CORE_WHEEL"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install "$CORE_WHEEL"
"$VENV_PYTHON" -m pip install -e "${REPO_ROOT}[dev]"
"$VENV_PYTHON" -m pip check

printf 'Portia development environment is ready.\n'
printf 'Authenticated Core wheel: %s\n' "$CORE_WHEEL"
printf 'Activate it with: source .venv/bin/activate\n'
