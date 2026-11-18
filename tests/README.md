# Корневые тесты FinDocs

В `tests/` живут интеграционные Python-тесты верхнего уровня (`test_api_documents.py`, `test_smoke.py`). Модульные и интеграционные тесты самого backend — в `backend/tests/`; тесты React/Vite — рядом с кодом в `frontend/src/`. Общие QA-материалы — в [`qa/`](../qa/README.md).

Из корня репозитория после установки окружения:

```bash
source .venv/bin/activate
cd backend
FINDOCS_LLM_PROVIDER=mock PYTHONPATH=.. python -m pytest tests/ ../tests/ -q
```

Не запускать только `tests/` из корня без корректного `PYTHONPATH`: тесты импортируют как `app`, так и `backend.app`. CI настроен на запуск из `backend/` с `PYTHONPATH=..`. Реальная Ollama в unit-тестах не нужна.
