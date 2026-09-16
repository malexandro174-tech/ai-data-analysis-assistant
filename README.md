# AI Data Analyst Workspace

AI-ассистент для анализа CSV, Excel, JSON и изображений с графиками, отчётами и мультимодальным анализом. Workspace хранит файлы и артефакты в изолированной сессии, а вычисления выполняет локальными проверяемыми инструментами.

## Проблема и решение

Табличные данные часто требуют нескольких несвязанных инструментов: просмотра структуры, расчёта метрик, построения графиков и подготовки отчёта. Сервис объединяет эти шаги в один веб-workspace, не передавая полный набор данных языковой модели и не предоставляя ей выполнение произвольного кода.

## Возможности

- загрузка CSV, XLSX, XLS, JSON, PNG, JPEG и WEBP;
- детерминированный анализ схемы, пропусков, уникальных значений и числовых метрик;
- пять типов графиков: line, bar, histogram, scatter и pie;
- DOCX-отчёт и Markdown summary как зарегистрированные скачиваемые артефакты;
- multimodal-анализ изображений через DeepSeek и Credential/Access Broker;
- history limit, session isolation, retention dry-run и health endpoint.

## Архитектура

```text
User → Web Workspace → FastAPI
                         ├─ Chat / Upload / Actions
                         ├─ File Service → Analysis Tools
                         └─ Validated Action Planner → Chart / Report / Summary → Artifact Registry → Download

Access & Integration Broker → DeepSeek Multimodal
```

LLM получает только ограниченный data context, формирует Pydantic-валидированный план и никогда не исполняет tools самостоятельно. Pandas, matplotlib и python-docx выполняют все расчёты и создают артефакты локально.

## Поддерживаемые файлы

| Тип | Назначение |
| --- | --- |
| CSV, XLSX, XLS, JSON | preview, profiling, charts, DOCX и Markdown |
| PNG, JPEG, WEBP | безопасное хранение и visual analysis |

Размер файла, строки, столбцы и pixels ограничены конфигурацией. Проверяются extension, content signature, empty files, image dimensions и path traversal.

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

`ANALYST_BROKER_URL` должен указывать на утверждённый private Broker. Не добавляйте provider API key в `.env`, код или Docker image.

## Безопасность

- действия ограничены allowlist: `preview`, `analyze`, `generate_chart`, `generate_report`, `save_summary`;
- download выполняется только по зарегистрированному artifact ID в текущей сессии;
- содержимое ячеек и изображений рассматривается как данные, а не инструкции;
- PostgreSQL и внешние credentials этому сервису не требуются;
- storage расположен в persistent volumes, а порт приложения привязан к localhost для reverse proxy.

## Tests

```bash
docker compose run --rm web pytest -q
```

Набор покрывает upload validation, CSV/XLSX/JSON analysis, column classification, charts, DOCX, artifact isolation, structured plans, prompt injection и policy denial.

## Ограничения и roadmap

Текущая версия предназначена для компактных файлов в пределах resource limits. Следующие шаги: версионирование семантических профилей, scheduled reports, агрегированные cohort dashboards и SSO для корпоративных workspace.

Для оценки retention без удаления используйте `python scripts/run_retention.py`; только явный флаг `--apply` удаляет уже просроченные файлы.
