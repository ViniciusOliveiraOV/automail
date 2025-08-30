from app.nlp.classifier import classify_text, classify_text_with_confidence


def test_classify_simple_productive():
    txt = "Por favor, envie o relatório até amanhã."
    label = classify_text(txt)
    assert label == "Produtivo"


def test_classify_simple_unproductive():
    txt = "Feliz aniversário! Tudo de bom."
    label = classify_text(txt)
    assert label == "Improdutivo"


def test_classify_confidence_and_ml_flag():
    txt = "Hi, can you update the status of the ticket?"
    label, conf, used_ml = classify_text_with_confidence(txt)
    assert label in ("Produtivo", "Improdutivo")
    assert 0.0 <= conf <= 1.0
    assert isinstance(used_ml, bool)
