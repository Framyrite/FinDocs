
# FinDocs Backend

Серверная часть FinDocs на Python 3.12 и FastAPI.

## Реализованные компоненты

- `GET /health` — проверка доступности HTTP-приложения.
- `Settings` — конфигурация через переменные окружения и `.env`.
- `LLMAdapter` — интерфейс для подключения языковой модели.
- `MockLLM` — тестовый адаптер без обращения к реальной LLM.
- `app/processing/` — обработка TXT и разбиение текста на чанки.

MockLLM не выполняет RAG и не генерирует настоящие ответы. Загрузка документов через HTTP, база данных и векторный поиск пока не реализованы.

## Требования

- Python 3.12.
- Доступ к PyPI для первоначальной установки зависимостей.
- Токенизатор `multilingual-e5-small` для TXT-обработки и соответствующих тестов.

## Установка

Все команды выполняются из каталога `backend`.

### Linux / macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

`requirements.txt` содержит зависимости приложения.
`requirements-dev.txt` дополнительно устанавливает pytest, httpx и Ruff.

В существующем окружении повторно создавать `.venv` не нужно.

## Конфигурация

При необходимости создайте `.env` на основе `.env.example`.

Linux / macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Не перезаписывайте существующий `.env`, если в нём уже есть локальные настройки.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `FINDOCS_APP_NAME` | `FinDocs Backend` | Название приложения |
| `FINDOCS_DEBUG` | `false` | Режим отладки FastAPI |

Приоритет настроек:

1. Переменные окружения процесса.
2. `backend/.env`.
3. Значения по умолчанию.

Путь к `.env` определяется относительно `config.py`, поэтому запуск не зависит от текущей рабочей директории.

Настройки валидируются через Pydantic. Пустое название приложения и некорректное значение `FINDOCS_DEBUG` вызывают ошибку валидации.

Настройки не кешируются: каждый вызов `create_app()` без явных настроек создаёт новый экземпляр `Settings`. Уже запущенное приложение не перечитывает `.env` автоматически — после изменения настроек перезапустите сервер.

## Запуск сервера

Из каталога `backend`, с активированным виртуальным окружением:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Остановка сервера: `Ctrl+C`.

При необходимости из корня репозитория:

```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Используйте Python из виртуального окружения `backend/.venv`.

## Проверка HTTP API

После запуска сервера откройте:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/openapi.json

Проверка через терминал:

```bash
curl -i http://127.0.0.1:8000/health
```

Ожидаются HTTP 200 и JSON:

```json
{"status":"ok"}
```

`/health` подтверждает доступность HTTP-приложения, а не готовность базы данных, RAG или реальной LLM.

## LLM-адаптер

Основной интерфейс:

```python
LLMAdapter.generate(question: str, context: str) -> str
```

`context` содержит заранее подготовленный текст. Пустой контекст допустим.

- Пустой или пробельный вопрос вызывает `ValueError`.
- Нестрочные аргументы вызывают `TypeError`.
- `MockLLM` возвращает детерминированный тестовый ответ.

Ручная проверка:

```bash
python -c "from app.main import app; print(app.state.llm_adapter.generate('Что такое FinDocs?', 'Тестовый контекст'))"
```

`create_app(settings=..., llm_adapter=...)` позволяет подменять конфигурацию и реализацию LLM при тестировании.

## Обработка TXT

Модуль `app/processing/` выполняет обработку TXT в памяти.

Поддерживается:

- UTF-8 и UTF-8 BOM.
- Сохранение пробелов и переносов строк.
- Проверка пустых документов и некорректной кодировки.
- Разбиение по 350 токенов с перекрытием 50 токенов.
- Точные символьные диапазоны чанков.
- Детерминированные UUID5 для блоков и чанков.

### Установка токенизатора

Файл `tokenizer.json` не хранится в Git и не загружается автоматически при работе приложения.

Из каталога `backend`:

```bash
mkdir -p models/multilingual-e5-small

curl -fL --retry 3 \
  "https://huggingface.co/intfloat/multilingual-e5-small/resolve/ada7b62be30f82b0bc5da131b0477721c8fc14e9/tokenizer.json" \
  -o models/multilingual-e5-small/tokenizer.json
```

Проверка SHA-256 в Linux / macOS:

```bash
echo "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39  models/multilingual-e5-small/tokenizer.json" \
  | shasum -a 256 -c -
```

Ожидаемый результат:

```text
models/multilingual-e5-small/tokenizer.json: OK
```

Используется `tokenizers==0.23.3`.

Альтернативное расположение токенизатора можно указать через `FINDOCS_TOKENIZER_DIR`.

### Пример использования

```python
from uuid import uuid4

from app.processing import process_txt

result = process_txt(
    "Привет, FinDocs!".encode("utf-8"),
    uuid4(),
)

print(result.blocks)
print(result.chunks)
```

Модуль не сохраняет документы, не строит embeddings и не выполняет RAG.

## Автоматические проверки

Все команды выполняются из каталога `backend` с активированным виртуальным окружением.

Тесты базового backend и TXT:

```bash
python -m pytest -q
```

Полный набор тестов, включая QA-проверки из корневого каталога:

```bash
PYTHONPATH=.. python -m pytest tests/ ../tests/ -q
```

Проверка импортов, ошибок и стиля:

```bash
python -m ruff check .
```

Проверка форматирования:

```bash
python -m ruff format --check .
```

Проверка совместимости установленных зависимостей:

```bash
python -m pip check
```

GitHub Actions запускает совместный набор Unit- и QA-тестов при изменениях в pull request к `main`.

## Интеграция с frontend

Для локальной разработки с React/Vite предпочтительно использовать Vite dev proxy, направляющий API-запросы на FastAPI.

Конкретная настройка proxy должна быть согласована с frontend-разработчиком и архитектором. На текущем этапе интеграция через браузер не подтверждена.

Vite dev proxy предназначен для локальной разработки и не заменяет настройку сетевого взаимодействия при развёртывании приложения.
