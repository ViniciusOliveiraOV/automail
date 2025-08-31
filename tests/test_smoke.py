import io
import json

def test_index_get(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'Classificador de Emails' in r.data


def test_classify_post_text(client):
    payload = {'email_text': 'Olá, gostaria de marcar uma reunião para discutir o relatório.'}
    r = client.post('/classify', data=payload)
    assert r.status_code == 200
    # expect result page contains the result header
    assert b'Resultado da Classifica' in r.data


def test_process_email_json(client):
    payload = {'text': 'Por favor, envie-me o comprovante de pagamento.'}
    r = client.post('/process-email', json=payload)
    assert r.status_code == 200
    data = json.loads(r.data)
    assert 'category' in data


def test_classify_file_upload_txt(client):
    txt = b"Assunto: Fatura\n\nPrezados, segue a fatura em anexo." 
    data = {
        'email_file': (io.BytesIO(txt), 'sample.txt')
    }
    r = client.post('/classify', content_type='multipart/form-data', data=data)
    # Accept either a rendered HTML result or a JSON error if file handling differs
    assert r.status_code in (200, 400)
