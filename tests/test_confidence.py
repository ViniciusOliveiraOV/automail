import pytest
from app.nlp.classifier import classify_text_with_confidence, _try_ml_classify


def test_high_confidence_heuristic():
    # text with action verb and work context -> high heuristic confidence
    text = "Por favor, atualize o status do ticket e envie o relatório"
    label, conf, used_ml = classify_text_with_confidence(text)
    assert label in ("Produtivo", "Improdutivo")
    assert conf >= 0.6
    assert used_ml is False


def test_low_confidence_needs_human(monkeypatch):
    # ambiguous short text -> low confidence, no ML available
    text = "batata frita javascript"
    # ensure ML is not available
    monkeypatch.setattr('app.nlp.classifier._ml_clf', None)
    # also ensure env var not set
    monkeypatch.delenv('LOAD_MODEL', raising=False)
    # ensure hard-filters don't mark the text as garbled/spammy for this test
    monkeypatch.setattr('app.nlp.classifier._looks_garbled', lambda t: False)
    monkeypatch.setattr('app.nlp.classifier._looks_spammy', lambda t: False)
    # force low scoring so heuristic confidence is low
    monkeypatch.setattr('app.nlp.classifier._score_text', lambda t: (0, 0, {}))
    label, conf, used_ml = classify_text_with_confidence(text)
    assert conf < 0.45
    assert used_ml is False


def test_low_confidence_ml_fallback(monkeypatch):
    # ambiguous short text but ML returns a label
    text = "batata frita javascript"

    def fake_ml(text_in):
        return "Improdutivo"

    # monkeypatch the ML classify function
    monkeypatch.setattr('app.nlp.classifier._looks_garbled', lambda t: False)
    monkeypatch.setattr('app.nlp.classifier._looks_spammy', lambda t: False)
    # force low scoring so heuristic confidence is low and ML fallback runs
    monkeypatch.setattr('app.nlp.classifier._score_text', lambda t: (0, 0, {}))
    monkeypatch.setattr('app.nlp.classifier._try_ml_classify', lambda t: fake_ml(t))
    # set env var to simulate that ML was requested
    monkeypatch.setenv('LOAD_MODEL', '1')
    label, conf, used_ml = classify_text_with_confidence(text)
    assert used_ml is True
    assert label == "Improdutivo"
    assert conf >= 0.75
