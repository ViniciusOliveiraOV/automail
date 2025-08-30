from bs4 import BeautifulSoup


def test_classify_post_text(client):
    resp = client.post('/classify', data={'text': 'Por favor, confirme a reunião amanhã.'})
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    # score fragment should be present
    frag = soup.select_one('#classifier-fragment')
    assert frag is not None
    # decision should be visible
    assert 'Produtivo' in html or 'Improdutivo' in html

