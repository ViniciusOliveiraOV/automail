import pytest
from app.nlp.preprocess import preprocess_text

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("This is a sample email text with some stop words.", "sample email text stop words."),
        ("running runner ran", "run run run"),
        ("better best", "good good"),
    ],
)
def test_preprocess_examples(input_text: str, expected: str) -> None:
    """
    Verifica remoção de stopwords, stemming/lemmatization simplificados e normalização.
    Ajuste 'expected' se sua função preprocess_text produzir formato diferente.
    """
    out = preprocess_text(input_text)
    assert out == expected