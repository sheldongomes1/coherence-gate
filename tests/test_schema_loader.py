from coherence_gate.schema_loader import build_extraction_model, extraction_json_schema, load_schema


def test_schema_has_20_fields_19_compared():
    s = load_schema()
    assert len(s.fields) == 20
    assert len(s.comparison_keys) == 19
    assert "coupon_rate_basis" not in s.comparison_keys


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
