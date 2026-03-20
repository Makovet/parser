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
  --output data/output/1.json
```

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
- Классификация абзацев: `src/qms_doc_parser/classifiers/style_classifier.py`
- Трекинг секций: `src/qms_doc_parser/trackers/section_tracker.py`
- Парсинг таблиц: `src/qms_doc_parser/parsers/table_parser.py`
- Реестр стилей: `configs/style_registry_adm_tem_011_b.yaml`
