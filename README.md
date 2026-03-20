# qms-doc-parser

Утилита парсит DOCX-документы шаблона СМК (QMS) и превращает их в структурированный JSON.

## Что делает программа

1. Загружает реестр стилей из YAML-конфига.
2. Читает `.docx` через `python-docx`.
3. Идёт по блокам документа в исходном порядке (абзацы и таблицы).
4. Классифицирует абзацы по стилям (с fallback по текстовым паттернам).
5. Для заголовков строит контекст секций (вложенность, `section_path`, `parent_section_id`).
6. Для таблиц извлекает нормализованную сетку и вычисляет `row_span`/`col_span` merged-ячеек.
7. Собирает итоговую модель `ParserDocument` и пишет JSON на диск.

## Быстрый запуск

```bash
python -m pip install -e .
```

```bash
python scripts/run_parse.py data/input/1.docx \
  --registry configs/style_registry_adm_tem_011_b.yaml \
  --output /tmp/1.json
```

## Быстрый старт для разработчика

1. Установите проект в editable-режиме:

```bash
python -m pip install -e .
```

2. Запустите тесты из корня репозитория:

```bash
python -m pytest -q
```

3. Запустите пример разбора документа:

```bash
python scripts/run_parse.py data/input/1.docx \
  --registry configs/style_registry_adm_tem_011_b.yaml \
  --output /tmp/1.json
```

4. При необходимости отдельно выгрузите compact review candidates для следующего reviewer-слоя:

```bash
python scripts/run_review_candidates.py data/input/1.docx \
  --registry configs/style_registry_adm_tem_011_b.yaml \
  --output /tmp/1.review_candidates.json
```

Локальные результаты разбора в `data/output/` и временные JSON-файлы не должны коммититься: каталог предназначен только для локальных запусков.

## Sample integration policy

- Для `data/input/1.docx` используется интеграционный тест на ключевые инварианты парсинга.
- Тест проверяет формирование summary, наличие секций, таблиц и ожидаемых зон документа.
- Отдельный review-candidates output строится поверх детерминированного parser output и не меняет итоговые `block_type`.
- `data/output/` зарезервирован для локально сгенерированных файлов и исключён из git.

## Запуск по клику через ярлык

В репозитории добавлен ярлык `qms-doc-parser.desktop` и GUI-ланчер `scripts/launch_parser_gui.py`.

1. Установите зависимости:

```bash
python -m pip install -e .
```

2. Сделайте ярлык исполняемым:

```bash
chmod +x qms-doc-parser.desktop
```

3. Переместите или скопируйте `qms-doc-parser.desktop` на рабочий стол/в нужную папку.
4. Открывайте ярлык двойным кликом.
5. В появившемся окне выберите `.docx`, затем укажите, куда сохранить `.json`.

## Ключевые точки входа

- CLI: `scripts/run_parse.py`
- GUI-ланчер: `scripts/launch_parser_gui.py`
- API-обёртка записи JSON: `src/qms_doc_parser/main.py`
- Основной pipeline: `src/qms_doc_parser/pipeline/parser_pipeline.py`
- Review candidates builder: `src/qms_doc_parser/review/review_candidates.py`
- Классификация абзацев: `src/qms_doc_parser/classifiers/style_classifier.py`
- Трекинг секций: `src/qms_doc_parser/trackers/section_tracker.py`
- Парсинг таблиц: `src/qms_doc_parser/parsers/table_parser.py`
- Реестр стилей: `configs/style_registry_adm_tem_011_b.yaml`
