from coherence_gate.schema_loader import build_extraction_model, extraction_json_schema, load_schema


def test_v1_schema_has_20_fields_19_compared():
    s = load_schema()  # termsheet_v1 (v0.1 record)
    assert len(s.fields) == 20
    assert len(s.comparison_keys) == 19
    assert "coupon_rate_basis" not in s.comparison_keys


def test_v2_note_schema_adds_index_fields():
    from coherence_gate.schema_loader import schema_for
    s = schema_for("note")
    assert s.version == "2" and len(s.fields) == 27 and len(s.comparison_keys) == 26
    assert [f.name for f in s.fields if f.name.startswith("index_")][0] == "index_administrator"


def test_critical_count():
    assert sum(f.critical for f in load_schema().fields) == 15


def test_extraction_model_requires_every_field():
    m = build_extraction_model()
    js = extraction_json_schema()
    assert set(js["required"]) == set(load_schema().names)
    assert m.__name__ == "TermSheetExtractionV1"


def test_enum_and_absent_flags():
    s = load_schema()
    assert s.spec("barrier_type").enum == ("european", "american", "none")
    assert s.spec("barrier_level_pct").may_be_absent
    assert not s.spec("notional").may_be_absent
