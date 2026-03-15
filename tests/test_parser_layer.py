from parser_layer import ParserLayerV03


def test_registry_style_and_toc_flag():
    parser = ParserLayerV03()
    doc = parser.parse(
        "doc.docx",
        [
            {"raw_text": "Содержание", "source_style": "0_ИЦЖТ_Заголовок_Структурный (вне содержания)"},
            {"raw_text": "1 Назначение", "source_style": "Оглавление 1"},
        ],
    )
    assert doc["blocks"][1]["block_type"] == "toc_item"
    assert doc["blocks"][1]["document_zone"] == "toc"
    assert doc["blocks"][1]["flags"]["is_generated_toc_entry"] is True


def test_template_instruction_detection_and_zone():
    parser = ParserLayerV03()
    doc = parser.parse(
        "doc.docx",
        [{"raw_text": "ВНИМАНИЕ! Удалить при разработке документа", "source_style": None}],
    )
    block = doc["blocks"][0]
    assert block["block_type"] == "template_instruction"
    assert block["document_zone"] == "template_instruction"
    assert block["flags"]["is_deletable_template_content"] is True


def test_composite_note_object():
    parser = ParserLayerV03()
    doc = parser.parse(
        "doc.docx",
        [
            {"raw_text": "Примечание", "source_style": "05_ИЦЖТ_Примечание_слово"},
            {"raw_text": "Текст примечания", "source_style": "05_ИЦЖТ_Примечание_текст после"},
        ],
    )
    notes = doc["composite_objects"]["notes"]
    assert len(notes) == 1
    assert notes[0]["full_text"] == "Примечание — Текст примечания"
