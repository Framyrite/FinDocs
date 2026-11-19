# FinDocs

FinDocs — учебное веб-приложение для вопросов по загруженным TXT-документам. Ответы локальной языковой модели сопровождаются проверяемыми цитатами; если сведений недостаточно, приложение отказывает в ответе.

**Статус на 19 ноября 2026 года:** рабочий TXT-MVP. Frontend подключён к реальному FastAPI (PR #16), backend поддерживает локальную Ollama (Backend 0.7–0.8). Локальный интеграционный smoke-тест с Qwen 3.5 4B проведён; это не означает готовность production.

## Что работает

- Загрузка одного или нескольких UTF-8 TXT (до 10 МиБ на файл), обработка, статусы, поиск по названию и удаление.
- Выбор области поиска: все готовые документы либо явно выбранные. Пустой явный выбор блокирует отправку.
- Лексический поиск по чанкам документов, `POST /chat/ask` и ответы со списком исходных цитат.
- Генерация через локальную Ollama либо серверный MockLLM для разработки.
- Frontend React + TypeScript + Vite с HTTP-клиентом и dev-прокси `/api` → `http://127.0.0.1:8000`.
- Unit/integration/QA-проверки и GitHub Actions для обеих частей.

**Пока нет:** PDF/DOCX, embeddings, векторной базы, семантического поиска, авторизации, истории чатов, мобильного UI и production-развёртывания. `multilingual-e5-small` используется здесь как **токенизатор TXT**, не как embedding-модель.

## Быстрая установка

**Требования:** Python 3.12, Node.js 22.12+ (или актуальная совместимая LTS), npm, curl и доступ к пакетным репозиториям. Для реальных ответов дополнительно нужна установленная Ollama и скачанная модель.

macOS / Linux из корня репозитория:

```bash
./scripts/setup.sh
```

Windows PowerShell:

```powershell
.\scripts\setup.ps1
```

Сценарии создают корневую `.venv`, устанавливают Python-зависимости разработки и frontend-пакеты через `npm ci`, скачивают закреплённый TXT-токенизатор с проверкой SHA-256 и **не перезаписывают существующие `.env`**. Ollama и веса LLM автоматически не скачиваются.

Для ручной установки см. [backend/README.md](backend/README.md) и [frontend/README.md](frontend/README.md).

## Локальный запуск

Перед использованием Ollama убедитесь, что её API отвечает на `http://127.0.0.1:11434/api/tags` и модель `qwen3.5:4b-q4_K_M` установлена (`ollama list`). При необходимости запустите службу Ollama и выполните `ollama pull qwen3.5:4b-q4_K_M`.

**Терминал 1 — backend** из корня:

```bash
source .venv/bin/activate
cd backend
FINDOCS_LLM_PROVIDER=ollama FINDOCS_LLM_MODEL=qwen3.5:4b-q4_K_M \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Для работы без Ollama используйте `FINDOCS_LLM_PROVIDER=mock`.

**Терминал 2 — frontend** из корня:

```bash
cd frontend
npm run dev
```

Откройте <http://localhost:5173/>. `GET http://127.0.0.1:8000/health` должен вернуть `{"status":"ok"}`. В dev-режиме frontend обращается к настоящему API, если `VITE_USE_MOCK` не равен `true`.

## Проверки

После установки можно запустить все проверки одной командой: `./scripts/check.sh` (macOS/Linux) или `.\scripts\check.ps1` (Windows PowerShell). Она запускает Ruff, pip check, pytest, frontend lint, сборку и Vitest.

Эквивалентные команды вручную:

Backend (из корня, с активной `.venv`):

```bash
cd backend
python -m ruff check . ../tests/
python -m ruff format --check . ../tests/
FINDOCS_LLM_PROVIDER=mock PYTHONPATH=.. python -m pytest tests/ ../tests/ -q
```

Frontend (из `frontend/`):

```bash
npm run lint
npm run build
npm test -- --run
```

Зависимости **не объединены в один файл**: Python — `backend/requirements.txt` и `requirements-dev.txt`; Node.js — `frontend/package.json` и `package-lock.json`. Используйте `npm ci` для воспроизводимой установки. Отчёт `npm audit` разбирается отдельно; не применяйте `npm audit fix` автоматически.

## Структура и документация

| Путь | Назначение |
| --- | --- |
| `backend/app/` | FastAPI, документы, TXT processing, lexical retrieval, чат и Ollama-адаптер |
| `backend/tests/` | Python-тесты модулей backend |
| `frontend/src/` | Интерфейс React/TypeScript и тесты компонентов |
| `qa/test_data/`, `qa/reports/` | QA-фикстуры, сравнения моделей и отчёты |
| `tests/` | Корневые интеграционные Python-тесты |
| `.github/workflows/` | GitHub Actions |
| `scripts/` | Установка окружения |
| `docs/current-architecture.md` | **Реализованная** архитектура на текущем этапе |
| `architecture.md` | Ранее согласованная **целевая/проектная** архитектура (включает будущие компоненты) |
| `decisions.md` | Журнал архитектурных решений |

Подробности: [Backend](backend/README.md) · [Frontend](frontend/README.md) · [QA](qa/README.md) · [Тесты](tests/README.md) · [Текущая архитектура](docs/current-architecture.md).

## Работа с репозиторием

Изменения идут в тематических ветках и небольших PR в `main`; перед merge обязательны проверки CI и независимое ревью. Не добавляйте в Git `.env`, локальные документы из `backend/data/`, каталоги `.venv/` и `node_modules/`. Тестовый файл `qa/test_data/pdf_text_injection.txt` содержит намеренно вредоносную инструкцию: использовать только как данные для QA, никогда как руководство к действиям.
