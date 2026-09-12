from types import SimpleNamespace as NS

from coherence_gate.extract.schema_guard import locate
from coherence_gate.ingest.parser import compose_markdown


def test_compose_drops_footers_and_rejoins_split_sentence():
    chunks = [NS(content="x", elements=[{"type": "section-header", "content": "3. Coupon"},
                                          {"type": "text", "content": "Memory feature: if a Coupon is not paid, that Coupon is"},
                                          {"type": "footer", "content": "Northbridge — Programme"}, {"type": "footer", "content": "Page 1 of 2"}]),
              NS(content="y", elements=[{"type": "text", "content": "not lost. It will be paid later."}, {"type": "table", "content": "<table><tr><td>a</td></tr></table>"}])]
    md = compose_markdown(chunks)
    assert "Page 1 of 2" not in md and "Northbridge — Programme" not in md and md.startswith("## 3. Coupon")
    s, e = locate("Memory feature: if a Coupon is not paid, that Coupon is not lost. It will be paid later.", md)
    assert md[s:e].startswith("Memory feature") and md[s:e].endswith("later.")
    assert "<table>" in md
