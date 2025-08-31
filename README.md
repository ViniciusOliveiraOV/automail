# Automail - App de classificação de e-mails 

Este projeto é uma aplicação web que automatiza a classificação de e‑mails em duas categorias: **Produtivo** (requer ação/resposta) e **Improdutivo** (não requer ação imediata). A aplicação usa técnicas de processamento de linguagem natural (NLP) e regras heurísticas, com opção de inferência por modelos de Aprendizado de Máquina (Machine Learning/ML).

## Funcionalidades


Aplicação Flask para classificar e‑mails em duas categorias: **Produtivo** (requer ação/resposta) e **Improdutivo** (não requer ação imediata).
O sistema combina um classificador baseado em regras (heurísticas) com um fallback opcional por ML e integração opcional a APIs LLM para casos ambíguos.

## Estrutura do projeto

  ```
  email-classifier-app/
  ├── cypress.config.js
  ├── docker-compose.dev.yml
  ├── docker-compose.prod.yml
  ├── docker-compose.yml
  ├── Dockerfile
  ├── Makefile
  ├── package.json
  ├── Procfile
  ├── README_CYPRESS.md
  ├── README.md
  ├── requirements.txt
  ├── visao-geral.png
  ├── app/
  │   ├── __init__.py
  │   ├── config.py
  │   ├── main.py
  │   ├── routes.py
  │   ├── __pycache__/
  │   │   ├── __init__.cpython-313.pyc
  │   │   ├── config.cpython-313.pyc
  │   │   ├── main.cpython-313.pyc
  │   │   └── routes.cpython-313.pyc
  │   ├── ai/
  │   │   ├── __init__.py
  │   │   ├── client.py
  │   │   └── __pycache__/
  │   ├── nlp/
  │   │   ├── __init__.py
  │   │   ├── classifier.py
  │   │   ├── preprocess.py
  │   │   └── __pycache__/
  │   ├── static/
  │   │   ├── css/
  │   │   └── js/
  │   ├── templates/
  │   │   ├── index.html
  │   │   └── result.html
  │   └── utils/
  │       ├── __init__.py
  │       ├── mail_client.py
  │       └── pdf_parser.py
  ├── backend/
  │   └── README.md
  ├── cypress/
  │   ├── e2e/
  │   │   └── classify_spec.cy.js
  │   ├── fixtures/
  │   │   └── sample_email.txt
  │   └── support/
  │       ├── commands.js
  │       └── e2e.js
  ├── frontend/
  ├── sample_emails/
  │   ├── productive_example.txt
  │   └── unproductive_example.txt
  ├── scripts/
  │   └── check_classifier_html.py
  ├── templates/
  │   └── result.html
  └── tests/
    ├── conftest.py
    ├── manual_test_classifier.py
    ├── test_bart_zero_shot.py
    ├── test_classifier_api.py
    ├── test_classifier_logic.py
    ├── test_classifier.py
    ├── test_confidence.py
    ├── test_frontend_structure.py
    └── test_preprocess.py
  ```

  > Nota: arquivos de interesse: `app/nlp/classifier.py` (lógica principal), `app/routes.py` (upload/classify), `app/ai/client.py` (opcional LLM).

  ## Instalação e execução local

  1. Clone o repositório e entre na pasta:

  ```powershell
  git clone <repository-url>
  cd automail/email-classifier-app
  ```

  2. Recomendado: crie um virtualenv e instale dependências:

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

  3. Execute a aplicação em modo de desenvolvimento:

  ```powershell
  # define o app e roda
  $env:FLASK_APP='app'; flask run --host 127.0.0.1 --port 5000
  ```

  Alternativa (módulo):

  ```powershell
  python -m app.main
  ```

  Ao abrir `http://127.0.0.1:5000` cole/mande o texto do e‑mail ou anexe um PDF/TXT e envie o formulário.

  ## Testes

  Unit / integration (pytest)

  ```powershell
  pytest -q
  ```

  Cypress (E2E)

  1. Instale dependências Node (na raiz `email-classifier-app`):

  ```powershell
  npm install
  ```

  2. Rodar a aplicação localmente (ver passo anterior) e então:

  Abrir runner interativo:

  ```powershell
  npm run cypress:open
  ```

  Executar headless:

  ```powershell
  npm run cypress:run
  ```

  Observações:
  - Os testes E2E pressupõem que o app esteja em `http://127.0.0.1:5000` (veja `cypress.config.js` para alterar `baseUrl`).
  - Use sua ferramenta de tunelamento preferida se precisar expor o servidor a terceiros (não há dependência embutida a ngrok).

  ## Algoritmos e design (o que está acontecendo)

  Resumo do fluxo ao classificar um texto/PDF:

  1. Extração: PDFs são lidos por `utils/pdf_parser.py`. Se o PDF não tiver texto extraível, o sistema pode sinalizar para revisão ou usar OCR (Optical Character Recognition).
  2. Pré‑processamento: `nlp/preprocess.py` limpa, normaliza (lowercase), tokeniza e remove stopwords. Também reduz ruído (muitos símbolos, strings repetidas).
  3. Regras heurísticas (regra principal):
    - Lista de palavras‑chave produtivas (ex.: "revisar", "prazo", "confirma", "reunião") soma pontos.
    - Presença de perguntas com tokens significativos e contexto favorece Produtivo.
    - Detectores de spam/ruído (proporção símbolo/dígito, clusters de consoantes) penalizam e reduzem confiança.
    - Pontuação final por heurística é normalizada para produzir uma "confidence" (0.0–1.0).

  4. Fallback ML (opcional):
    - Se a configuração `LOAD_MODEL` estiver ativa e o score heurístico estiver em zona ambígua, o classificador carrega um modelo ML leve (ex.: logistic regression, SVM ou um ensemble simples) e usa features derivadas (bag‑of‑words ponderado, presence de keywords, proporções, n‑grams simples) para predizer e ajustar a confiança.
    - O ML não substitui regras críticas (p.ex. detectores de spam com alta certeza) — ele atua como comitê de desempate.

  5. LLM (opcional) - integração via `app/ai/client.py`:
    - Usado apenas quando habilitado por variável de ambiente e quando nem heurística nem ML entregam confiança suficiente.
    - O cliente monta um prompt com instruções claras (ex.: "Classifique o texto como Produtivo ou Improdutivo e explique brevemente a razão") e envia à API configurada (OpenAI, Hugging Face, Anthropic — dependendo da configuração).
    - O resultado do LLM é parseado e combinado com as heurísticas para gerar a decisão final; LLM é tratado como "consultor" e suas respostas são avaliadas por regras simples (p.ex. checagem de formato e de tokens) para evitar respostas inventadas.

  Confiança e explicabilidade
  - Cada decisão vem com uma `confidence` numérica e um campo `details` com as regras/features que mais contribuíram para a decisão. Isso facilita auditoria e ajuste dos limiares.

  ## Heurística ML - mais detalhes (como o ML é usado)

  - Treinamento: dataset mínimo esperado para treinar o classificador ML (fora deste repositório) consiste de textos rotulados (Produtivo/Improdutivo). Features simples: contagem TF, presença de keywords, razão símbolos/caracteres, tokens de pergunta, comprimento do texto, presença de anexo.
  - O pipeline do projeto usa o modelo apenas em runtime como fallback (inference). Para re‑treinar, exporte os exemplos rotulados e treine localmente usando scikit‑learn (processo fora do escopo do servidor web).
  - A predição ML retorna probabilidade que é combinada com o score heurístico por uma função ponderada (p.ex. weighted average com pesos configuráveis).

  ## APIs LLM - como integrar com segurança

  - O cliente em `app/ai/client.py` é um wrapper simples que aceita um prompt e retorna a resposta textual.
  - Configure a variável `HF_API_TOKEN` ou `OPENAI_API_KEY` (conforme suporte) no `.env` / ambiente para habilitar.
  - Recomendações de segurança:
    - Não exponha chaves em repositórios públicos.
    - Defina timeouts curtos e trate erros de rede com fallback para heurística/ML.
    - Normalize e sanitise a resposta do LLM antes de confiar nela (p.ex. confirmar que resposta contém "Produtivo" ou "Improdutivo").

  ## Docker (desenvolvimento e produção)

  O repositório contém `Dockerfile` e `docker-compose.yml` para facilitar execução isolada.

  Desenvolvimento (exemplo):

  ```powershell
  docker-compose -f docker-compose.dev.yml up --build
  ```

  Produção (exemplo mínimo):

  ```powershell
  docker build -t automail:latest .
  docker run -p 5000:5000 --env-file .env automail:latest
  ```

  Notas Docker:
  - Monte volumes para persistência ou logs se quiser inspecionar arquivos gerados.
  - Configure variáveis de ambiente (ex.: `LOAD_MODEL`, `ENABLE_OCR`, `HF_API_TOKEN`) via `--env-file` ou no `docker-compose`.

  ## Variáveis importantes (.env)
  - `SECRET_KEY` - Flask secret
  - `LOAD_MODEL` - se `1` carrega modelo ML para fallback
  - `MODEL_PATH` - caminho local para o modelo (se `LOAD_MODEL=1`)
  - `ENABLE_OCR` - se `1` ativa tentativa de OCR em PDFs (requer dependências)
  - `HF_API_TOKEN` / `OPENAI_API_KEY` - tokens para chamadas de LLM
  - `AI_DBG` - ativa logs adicionais para LLM/AI

  ## Contribuição e desenvolvimento

  - Tests: escreva pytest para lógica de classificação e pequenos testes de integração para `routes.py`.
  - CI: existe uma workflow que executa pytest e (opcionalmente) Cypress; ver `.github/workflows/ci.yml`.

  ## Como auditar uma decisão
  - Cada resposta da API `/classify` inclui `decision`, `confidence` e `details` (lista/objeto com scores por heurística, features relevantes e, se usado, resposta bruta do ML/LLM).
  - Use esses campos para depurar falsos positivos/negativos e ajustar listas de keywords e limiares.

  ## Suporte e dúvidas
  - Abra uma issue descrevendo o comportamento observado, anexando texto de exemplo e o payload `details` retornado pelo classificador.

  ---

  Projeto licenciado sob MIT. (Adicione `LICENSE` se desejar.)

  ```
