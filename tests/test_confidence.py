import pytest
from typing import Tuple, Dict, Any
from app.nlp.classifier import classify_text_with_confidence
import app.nlp.classifier as classifier

def _fake_score_text(t: str) -> Tuple[float, float, Dict[str, Any]]:
    return (0.0, 0.0, {})

def _fake_looks_spammy(t: str) -> bool:
    return False

def fake_ml(t: str) -> str:
    # return a label string consistent with classifier expectation
    return "Improdutivo"


def test_high_confidence_heuristic():
    # text with action verb and work context -> high heuristic confidence
    text = "Por favor, atualize o status do ticket e envie o relatório"
    label, conf, used_ml = classify_text_with_confidence(text)
    assert label in ("Produtivo", "Improdutivo")
    assert conf >= 0.6
    assert used_ml is False


def test_low_confidence_needs_human(monkeypatch: pytest.MonkeyPatch):
    # ambiguous short text -> low confidence, no ML available
    text = "batata frita javascript"
    # ensure ML is not available
    monkeypatch.setattr(classifier, '_ml_clf', None)
    # also ensure env var not set
    monkeypatch.delenv('LOAD_MODEL', raising=False)
    # ensure hard-filters don't mark the text as garbled/spammy for this test
    monkeypatch.setattr(classifier, '_looks_spammy', _fake_looks_spammy)
    # force low scoring so heuristic confidence is low
    monkeypatch.setattr(classifier, '_score_text', _fake_score_text)
    _, conf, used_ml = classify_text_with_confidence(text)
    assert conf < 0.45
    assert used_ml is False


def test_low_confidence_ml_fallback(monkeypatch: pytest.MonkeyPatch):
    # ambiguous short text but ML returns a label
    text = "batata frita javascript"
    # ensure spammy check returns False so ML path can run
    monkeypatch.setattr(classifier, '_looks_spammy', _fake_looks_spammy)
    # force low scoring so heuristic confidence is low and ML fallback runs
    monkeypatch.setattr(classifier, '_score_text', _fake_score_text)
    monkeypatch.setattr(classifier, '_try_ml_classify', fake_ml)
    # set env var to simulate that ML was requested
    monkeypatch.setenv('LOAD_MODEL', '1')
    label, conf, used_ml = classify_text_with_confidence(text)
    assert used_ml is True
    assert label == "Improdutivo"
    assert conf >= 0.75
