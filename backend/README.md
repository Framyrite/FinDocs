# Backend

Backend part of FinDocs.

Use this directory for server-side code, API endpoints, business logic, database access, and backend-specific configuration.


## Backend 0.2

## Локальный запуск

Требуется Python 3.12 и доступ к PyPI для первоначальной установки зависимостей.
Все команды ниже выполняются в каталоге `backend`.
В `requirements.txt` зафиксированы прямые и транзитивные зависимости,
использованные при проверке. Линтеры в зависимости приложения не включены.

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Копирование `.env.example` выполняется один раз. Если `.env` уже существует,
сохраните его настройки и добавьте недостающие параметры вручную.
При отсутствии `.env` используются значения по умолчанию.

Остановка сервера: `Ctrl+C`. Для запуска без автоматической перезагрузки
уберите `--reload`.

Из корня существующего репозитория сервер также можно запустить командой
`python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`.
Используйте Python из установленного виртуального окружения backend.

## Проверка доступности

После запуска откройте <http://127.0.0.1:8000/health> или выполните
в другом терминале:

```bash
curl -i http://127.0.0.1:8000/health
```

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Ожидаются HTTP `200`, `Content-Type: application/json` и ответ:

```json
{"status":"ok"}
```

Описание API: <http://127.0.0.1:8000/docs>.
Машинная спецификация: <http://127.0.0.1:8000/openapi.json>.
`/health` подтверждает доступность HTTP-приложения.

## Настройки

| Переменная | Значение по умолчанию | Назначение |
| --- | --- | --- |
| `FINDOCS_APP_NAME` | `FinDocs Backend` | Название приложения в OpenAPI |
| `FINDOCS_DEBUG` | `false` | Режим отладки FastAPI |

Порядок приоритета: переменные окружения процесса → `backend/.env` →
значения по умолчанию. Путь к `.env` определяется относительно `config.py`,
поэтому настройки читаются и при запуске из корня репозитория.
Посторонние параметры `.env` игнорируются. Пустое имя приложения и неверное
значение `FINDOCS_DEBUG` вызывают ошибку валидации при запуске.
Настройки читаются один раз на процесс; после изменения перезапустите сервер.
Хост и порт задаются параметрами Uvicorn в команде запуска.

## Ручная проверка LLM-адаптера

Из каталога `backend` выполните в том же виртуальном окружении:

```bash
python -c "from app.main import app; print(app.state.llm_adapter.generate('Что такое FinDocs?', 'FinDocs работает с учебными материалами.'))"
```

Ожидаемый результат:

```text
[MOCK] Тестовый ответ. Реальная LLM не подключена.
Вопрос: Что такое FinDocs?
Контекст: FinDocs работает с учебными материалами.
```

Контракт: `LLMAdapter.generate(question: str, context: str) -> str`.
`context` — уже подготовленный текст; пустая строка допустима.
Пустой вопрос вызывает `ValueError`, аргумент другого типа — `TypeError`.
Mock возвращает одинаковый результат для одинаковых входных данных.

`create_app(llm_adapter=...)` принимает любую реализацию `LLMAdapter`.
Зависимость выбирается в `main.py` и хранится в `app.state.llm_adapter`.
Будущая бизнес-логика обращается к интерфейсу `LLMAdapter`; конкретная
реализация подключается при создании приложения.

## TXT Processing

The backend includes a TXT processing module that converts UTF-8
documents into text blocks and overlapping chunks.

### Features

- UTF-8 and UTF-8 BOM support.
- Preservation of original whitespace and line breaks.
- Validation of empty and incorrectly encoded documents.
- Token-based chunking with 350 tokens per window and 50-token overlap.
- Exact character offsets for each chunk.
- Deterministic UUID5 identifiers for blocks and chunks.

### Requirements

- Python 3.12
- `tokenizers==0.23.3`
- The pinned `multilingual-e5-small` tokenizer file

### Installation

From the repository root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

### Download the tokenizer

The tokenizer file is not stored in Git.

From the `backend` directory:

```bash
mkdir -p models/multilingual-e5-small

curl -fL --retry 3 \
  "https://huggingface.co/intfloat/multilingual-e5-small/resolve/ada7b62be30f82b0bc5da131b0477721c8fc14e9/tokenizer.json" \
  -o models/multilingual-e5-small/tokenizer.json
```

Verify the SHA-256 checksum:

```bash
echo "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39  models/multilingual-e5-small/tokenizer.json" \
  | shasum -a 256 -c -
```

Expected output:

```text
models/multilingual-e5-small/tokenizer.json: OK
```

The tokenizer directory can also be configured using
`FINDOCS_TOKENIZER_DIR`.

The application does not automatically download the tokenizer.

### Running tests

From the `backend` directory:

```bash
python -m pytest -v tests/
```

The test suite covers TXT decoding, input validation,
chunk boundaries, character offsets, deterministic processing,
and tokenizer loading errors.

### Usage example

```python
from uuid import uuid4
from app.processing import process_txt

document_id = uuid4()

result = process_txt(
    "Привет, FinDocs!".encode("utf-8"),
    document_id,
)

print(result.blocks)
print(result.chunks)
```

### Scope

This module performs in-memory TXT processing only.

It does not implement document storage, HTTP endpoints,
vector search, RAG, or LLM integration.


## Запуск автотестов (CI/QA)

В проекте настроен совместный запуск Unit-тестов (`backend/tests/`) и независимых QA-проверок (`tests/` в корне). 

Требуется: **Python 3.12**. Все команды выполняются из директории `backend`:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ ../tests/ -q
```