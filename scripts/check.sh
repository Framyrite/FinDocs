#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Сначала выполните ./scripts/setup.sh" >&2; exit 1; }
(
  cd "$ROOT/backend"
  "$PY" -m pip check
  "$PY" -m ruff check . ../tests/
  "$PY" -m ruff format --check . ../tests/
  FINDOCS_LLM_PROVIDER=mock PYTHONPATH=.. "$PY" -m pytest tests/ ../tests/ -q
)
(
  cd "$ROOT/frontend"
  npm run lint
  npm run build
  npm test -- --run
)
echo "Все проверки успешно завершены."
