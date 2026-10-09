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

