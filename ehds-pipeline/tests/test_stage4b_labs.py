from app.pipeline.stage4b_labs import extract_labs


SAMPLE_LAB_TEXT = """
Hemoleucograma completa: [WBC) Leucocite=5.79 × 10^9/L, HGB) Hemoglobina=14.2 g/dL]
Bilirubina totala=0.626 mg/dL, TSH=2.1 mUI/L, cortizol seric= 0,46 ng/dl
"""


def test_hormone_panel_split():
    results = extract_labs(SAMPLE_LAB_TEXT)
    assert "TSH" in results.hormones or any("TSH" in k for k in results.hormones)
    assert "Bilirubina totala" in results.biochemistry or any(
        "Bilirubina" in k for k in results.biochemistry
    )
    assert len(results.cbc) >= 1
