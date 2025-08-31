# Instruções do Copilot para o repositório automail

Objetivo
- Ajudar contribuintes a serem produtivos rapidamente descrevendo a estrutura do projeto, pontos de entrada importantes, fluxos de execução e teste, e convenções recorrentes no código.

Orientação rápida
- Esta é uma pequena aplicação Flask em `app/` que classifica texto de e‑mail como `Produtivo` / `Improdutivo` usando um motor baseado em regras com um fallback opcional por sklearn e fallback por LLM.
- Pontos de entrada em tempo de execução:
  - `app/main.py` — factory da aplicação `create_app()` e entrada CLI quando executado como `python -m app.main`.
  - `app/__init__.py` — instância simples do Flask usada em alguns fluxos de desenvolvimento.
  - `app/routes.py` — rotas HTTP e handlers da interface web (`/`, `/classify`, `/process-email`).

Onde a lógica vive
- Classificador baseado em regras: `app/nlp/classifier.py` — pontuação central, filtros rígidos (`_looks_spammy`, `_looks_garbled`), overrides (`_apply_overrides`) e gerador de fragmento HTML (`_render_score_html`).
- Pré‑processamento: `app/nlp/preprocess.py` — normaliza e remove assinaturas/textos citados antes da pontuação.
- Parsing de PDF e utilitários: `app/utils/pdf_parser.py` e `app/utils/mail_client.py` (usados para extração de arquivos e leitura opcional de e‑mails).
- Integração AI/LLM: `app/ai/client.py` — wrappers para chamar a API de inferência HF (principal), Grok/x.ai (fallback) e caminho zero-shot BART; inclui cache e flags de debug.

Padrões e convenções importantes
- Labels estão em português: `Produtivo` e `Improdutivo` (strings exatas usadas nos testes e templates). Não altere essas strings sem atualizar testes e templates.
- O classificador expõe funções programáticas e helpers HTML:
  - `classify_text(text: str) -> str` — API canônica usada por testes e rotas.
  - `classify_text_with_confidence(text, ml_threshold=0.45) -> (label, confidence, used_ml)` — retorna confiança e se fallback ML foi usado.
  - `classify_text_html(text) -> (label, html_fragment)` — usado pela UI `/classify`; o fragmento HTML deve evitar estilos inline (o CSS do repositório controla aparência).
- Controle de CSS: `app/static/css/styles.css` contém paleta e badges do projeto. Mantenha `_render_score_html` semântico (use classes como `.score-card`, `.score-good`, `.score-bad`) para permitir restyling sem alterar Python.
- Comportamento opcional controlado por env:
  - `LOAD_MODEL=1` carrega `app/email_classifier_model.pkl` (caminho configurado em `classifier.py`) para habilitar fallback ML sklearn.
  - Chaves de API para AI são lidas por `app/ai/client.py` a partir de variáveis de ambiente (veja `app/config.py` para valores padrão).

Fluxos de desenvolvimento/execução/teste
- Local (edição rápida): ative seu venv e execute o servidor Flask em desenvolvimento a partir da raiz `email-classifier-app`:

```powershell
& .\.venv\Scripts\Activate.ps1
flask run --host 127.0.0.1 --port 5000
```

- Execute o módulo da app diretamente (usa a app factory):

```powershell
python -m app.main
```

- Testes: execute pytest a partir da raiz do repositório `email-classifier-app` (venv ativado):

```powershell
pytest -q
```

- Docker: veja `Dockerfile` e `docker-compose.yml` para execuções em contêiner. Há um `Makefile` com alvos de conveniência; inspecione `Makefile` para `make build` / `make up`.

Dicas e pontos de atenção para depuração
- Caminho de importação: muitos scripts esperam o diretório de trabalho como a raiz `email-classifier-app` para que `app` seja importável. Execute comandos Python a partir dessa pasta.
- Ao editar `_render_score_html`, evite embutir cores ou layout inline — use classes CSS em `app/static/css/styles.css`.
- O classificador define `last_decision_reason` para depuração; testes e rotas o leem — mantenha possíveis valores consistentes ao alterar a lógica.
- A extração de PDF usa `PyPDF2.PdfReader` em `routes.py` — erros em ambientes sem `PyPDF2` farão rotas que leem PDFs falharem; garanta que `requirements.txt` inclua pacotes necessários para o CI.

Pontos de integração entre componentes
- Routes -> NLP: `app/routes.py` importa `classify_text_html`, `classify_email`, `classify_text_with_confidence` e `get_last_decision_reason` de `app/nlp/classifier.py` — alterações nessas assinaturas quebram a UI web.
- Routes -> AI: `app/routes.py` chama `generate_response` de `app/ai/client.py` para gerar respostas sugeridas; o cliente AI tem cache e flags de debug.

Arquivos a inspecionar ao alterar comportamento
- `app/nlp/classifier.py` — regras de pontuação e filtros rígidos
- `app/nlp/preprocess.py` — normalização de texto e remoção de assinaturas
- `app/static/css/styles.css` + `app/templates/result.html` — apresentação visual dos fragmentos de classificação
- `app/ai/client.py` — fallbacks LLM, cache e flags de ambiente
- `tests/` — contém testes unitários que validam o comportamento do classificador; execute-os frequentemente ao alterar heurísticas

Exemplos mínimos (snippets úteis)
- Como obter classificação e fragmento HTML no REPL Python:

```python
from app.nlp.classifier import classify_text_html
label, html = classify_text_html(open('sample_emails/productive_example.txt').read())
```

- Como o fragmento HTML deve expor classes (exemplo esperado):

```html
<div class="score-panel">
  <div class="score-card"><h4>Produtivo</h4><div class="score-count">2</div></div>
  <div class="score-card"><h4>Improdutivo</h4><div class="score-count">0</div></div>
</div>
<ul class="score-list"><li class="score-details"><code>action_verb</code> <span class="score-good">+1</span></li></ul>
```

Quando preferir heurísticas vs ML/LLM
- Heurísticas são primárias; fallback ML é usado apenas quando confidence < `ml_threshold` e `LOAD_MODEL=1`.
- LLM (HF/Grok) é usado por `generate_response` para produzir respostas sugeridas, não para atribuição de label salvo quando explicitamente conectado nas rotas.

Se algo estiver pouco claro ou você preferir outro tom/formato, diga o que mudar e eu atualizo este arquivo conforme necessário.
