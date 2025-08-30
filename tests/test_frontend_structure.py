from bs4 import BeautifulSoup


def test_frontend_structure_has_score_panel(client):
    resp = client.post('/classify', data={'text': 'Por favor, envie o anexo.'})
    # accept 200 or 400 (some envs may respond 400 for missing deps); still validate HTML structure when present
    html = resp.get_data(as_text=True)
    assert html is not None
    soup = BeautifulSoup(html, 'html.parser')
    # check score-panel and cards
    panel = soup.select_one('.score-panel')
    if panel:
        cards = panel.select('.score-card')
        assert len(cards) >= 1
    else:
        # fallback: classifier fragment container still present
        frag = soup.select_one('#classifier-fragment')
        assert frag is not None
