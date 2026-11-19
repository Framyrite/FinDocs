#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
TOKENDIR="$ROOT/backend/models/multilingual-e5-small"
TOKEN="$TOKENDIR/tokenizer.json"
URL="https://huggingface.co/intfloat/multilingual-e5-small/resolve/ada7b62be30f82b0bc5da131b0477721c8fc14e9/tokenizer.json"
SHA="0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"

for tool in python3.12 node npm curl; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Не найдена команда: $tool" >&2; exit 1; }
done
node -e 'const [a,b]=process.versions.node.split(".").map(Number);if(a<22||(a===22&&b<12)){console.error("Нужен Node.js 22.12+");process.exit(1)}'

if [[ ! -x "$PY" ]]; then python3.12 -m venv "$ROOT/.venv"; fi
"$PY" -c 'import sys; assert sys.version_info[:2] == (3,12), "Нужен Python 3.12"'

echo "==> Python: установка и проверка зависимостей"
"$PY" -m pip install -r "$ROOT/backend/requirements-dev.txt"
"$PY" -m pip check

verify_tokenizer() {
  "$PY" - "$1" "$SHA" <<'PYCODE'
from pathlib import Path
import hashlib
import sys
digest = hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
if digest != sys.argv[2]:
    raise SystemExit(f"Неправильный SHA-256 токенизатора: {digest}")
print("SHA-256 токенизатора: OK")
PYCODE
}
mkdir -p "$TOKENDIR"
if [[ -f "$TOKEN" ]]; then
  verify_tokenizer "$TOKEN"
else
  TMP="$(mktemp "$TOKENDIR/.tokenizer.XXXXXX")"
  trap 'rm -f "$TMP"' EXIT
  curl --fail --location --retry 3 --silent --show-error "$URL" -o "$TMP"
  verify_tokenizer "$TMP"
  mv "$TMP" "$TOKEN"
  trap - EXIT
fi

for component in backend frontend; do
  if [[ ! -e "$ROOT/$component/.env" ]]; then
    cp "$ROOT/$component/.env.example" "$ROOT/$component/.env"
    echo "Создан $component/.env"
  fi
done

echo "==> Node.js: воспроизводимая установка npm ci"
(cd "$ROOT/frontend" && npm ci)

echo "Готово. Ollama и веса моделей устанавливаются отдельно."
echo "Backend: cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo "Frontend: cd frontend && npm run dev"
