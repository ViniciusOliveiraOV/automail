from app.ai.client import AIClient
import os

def test_junk_is_improductive():
    # enable debug to see HF logs during test if needed
    os.environ['AI_DBG'] = '1'
    os.environ['AI_DBG_RAW'] = '0'
    ai = AIClient()
    label = ai.classify_email('oi kkk testando')
    assert label.lower().startswith('improd'), f"Expected Improdutivo, got: {label}" 
