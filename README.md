# Automail - App de classificação de e-mails 

Este projeto é uma aplicação web que automatiza a classificação de e‑mails em duas categorias: **Produtivo** (requer ação/resposta) e **Improdutivo** (não requer ação imediata). A aplicação usa técnicas de processamento de linguagem natural (NLP) e regras heurísticas, com opção de inferência por modelos de Aprendizado de Máquina (Machine Learning/ML).

## Funcionalidades


## Estrutura do projeto

```
email-classifier-app/
  docker-compose.dev.yml
  docker-compose.prod.yml
  docker-compose.yml
  Dockerfile
  Makefile
  Procfile
  README.md
  requirements.txt
  app/
    __init__.py
    config.py
    main.py
    routes.py
    ai/
      client.py
    nlp/
      classifier.py
      preprocess.py
    static/
      css/
      js/
    templates/
      index.html
      result.html
    utils/
      mail_client.py
      pdf_parser.py
  backend/
    .env
    .gitkeep
    README.md
  frontend/
  sample_emails/
    productive_example.txt
    unproductive_example.txt
  templates/
    result.html
  tests/
    conftest.py
    manual_test_classifier.py
    test_bart_zero_shot.py
    test_classifier.py
    test_confidence.py
    test_preprocess.py
```

## Instalação

1. Clone o repositório:
   ```
   git clone <repository-url>
   cd automail
   ```

2. Crie e ative um ambiente virtual (recomendado) e instale dependências:
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```

3. Executar a aplicação:
   ```
   flask run
   ```
   ou
   ```
   python -m app.main
   ```

- Cole o texto do e‑mail ou anexe um PDF / TXT.
- Envie o formulário e veja o resultado com categoria e motivo (debug).

## Visão geral do pipeline de classificação

- Normalização: lowercase, remoção de stopwords e tokenização.
- Heurísticas:
  - Palavras‑chave produtivas (ex.: revisar, confirmar, prazo, reunião) → Produtivo.
  - Pergunta ("?") avaliada com tokens significativos e checagem anti‑spam.
  - Detectores de spam/ruído (clusters de consoantes, alta proporção de símbolos/dígitos) evitam falsos positivos.
- Se o modelo de IA estiver ligado, ele tenta decidir sozinho nos casos duvidosos; se não estiver, o sistema usa regras simples e previsíveis que sempre retornam um resultado.

- PDFs sem texto extraível podem ser marcados como Improdutivo ou sinalizados para revisão.
- OCR é opcional e requer dependências adicionais (Tesseract, Pillow, PyMuPDF).

- Automatizado: script IMAP que baixa mensagens e posta para `/classify`.
- Uso de ngrok recomendado para expor o servidor durante testes externos.

- Recomendado: PyPDF2 (`pip install PyPDF2`).
- Para OCR: PyMuPDF / Pillow / pytesseract e instalação do binário Tesseract (opcional).

- Ajuste limiares e listas de palavras conforme seu domínio.
- Registre sempre a razão da decisão (debug) para monitorar e melhorar regras.

- Pipeline de OCR (reconhecimento óptico de caracteres) mais robusto para PDFs escaneados.
- Interface para rotulagem manual e re‑treino do modelo ML.

## Contribuição

Contribuições são bem‑vindas. Abra uma issue ou envie um pull request.

## Licença

MIT

## .env / variáveis

Veja `.env.example` no repositório — ele contém todas as variáveis que o projeto usa (SECRET_KEY, HF_API_TOKEN, GROK_API_KEY, ENABLE_OCR, LOAD_MODEL, MODEL_PATH, IMAP_*, AI_DBG etc.).

## Como executar (resumido)

Recomendado (Docker):

```powershell
make build
make up
```

Alternativa (local, sem Docker):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

## Testes

Rode os testes com pytest:

```powershell
pytest -q
```

Projeto licenciado sob MIT. (Adicione o arquivo LICENSE se desejar.)
