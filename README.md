# Email Classifier App

Este projeto é uma aplicação web que automatiza a classificação de e‑mails em duas categorias: **Produtivo** (requer ação/resposta) e **Improdutivo** (não requer ação imediata). A aplicação usa técnicas de processamento de linguagem natural (NLP) e regras heurísticas, com opção de inferência por modelos de Aprendizado de Máquina (Machine Learning/ML).

## Funcionalidades

- Envio de e‑mails em `.txt` ou `.pdf` ou colagem do texto diretamente.
- Classificação automática em Produtivo / Improdutivo.
- Sugestões de resposta automáticas (quando configuradas).
- Interface web simples e orientada ao usuário.
- Campo "Debug" exibindo a razão da decisão.

## Estrutura do projeto

```
email-classifier-app
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── nlp
│   │   ├── __init__.py
│   │   ├── preprocess.py
│   │   └── classifier.py
│   ├── ai
│   │   ├── __init__.py
│   │   └── client.py
│   ├── utils
│   │   ├── __init__.py
│   │   └── pdf_parser.py
│   ├── templates
│   │   ├── index.html
│   │   └── result.html
│   └── static
│       ├── css
│       └── js
├── tests
├── sample_emails
├── Dockerfile
├── requirements.txt
└── README.md
```

## Instalação

1. Clone o repositório:
   ```
   git clone <repository-url>
   cd email-classifier-app
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

## Uso básico

- Abra `http://localhost:5000` no navegador.
- Cole o texto do e‑mail ou anexe um PDF / TXT.
- Envie o formulário e veja o resultado com categoria e motivo (debug).

## Visão geral do pipeline de classificação

O fluxo principal é: entrada do usuário → extração de texto → pré‑processamento → heurísticas / ML → resultado.

- Entrada prioritária: se o usuário colar texto no campo da página, esse texto é usado diretamente — é o caminho mais rápido e confiável.
- Upload de arquivo: se não houver texto no formulário, o app verifica se o usuário enviou um arquivo.
- Detecção de PDF: quando for um PDF, o sistema tenta extrair o texto interno (como copiar/colar) usando uma biblioteca chamada PyPDF2.
- Se a extração falhar: alguns PDFs são imagens (scan) e não contêm texto pesquisável — aí há uma segunda tentativa usando OCR (reconhecimento óptico de caracteres), que “lê” a imagem e transforma em texto.
- Outros formatos/arquivos: arquivos que não são PDF são lidos como bytes e tentamos decodificá‑los para texto; se não for possível, o app sinaliza que não conseguiu extrair conteúdo.
- Resultado prático: texto do formulário > texto extraído do PDF > texto obtido por OCR > arquivo sem texto; o app mostra um indicador (file_debug) informando qual método foi usado.
- Normalização: lowercase, remoção de stopwords e tokenização.
- Heurísticas:
  - Palavras‑chave produtivas (ex.: revisar, confirmar, prazo, reunião) → Produtivo.
  - Pergunta ("?") avaliada com tokens significativos e checagem anti‑spam.
  - Saudações/agradecimentos curtos sem indicadores de ação → Improdutivo.
  - Detectores de spam/ruído (clusters de consoantes, alta proporção de símbolos/dígitos) evitam falsos positivos.
- Se o modelo de IA estiver ligado, ele tenta decidir sozinho nos casos duvidosos; se não estiver, o sistema usa regras simples e previsíveis que sempre retornam um resultado.

## Critérios de classificação para PDFs

- PDFs com texto extraído são classificados pelo mesmo pipeline.
- PDFs sem texto extraível podem ser marcados como Improdutivo ou sinalizados para revisão.
- OCR é opcional e requer dependências adicionais (Tesseract, Pillow, PyMuPDF).

## Testes com Gmail

- Manual: copiar corpo do e‑mail e colar na área de texto.
- Automatizado: script IMAP que baixa mensagens e posta para `/classify`.
- Uso de ngrok recomendado para expor o servidor durante testes externos.

## Dependências e OCR (opcional)

- Recomendado: PyPDF2 (`pip install PyPDF2`).
- Para OCR: PyMuPDF / Pillow / pytesseract e instalação do binário Tesseract (opcional).

## Boas práticas

- Ajuste limiares e listas de palavras conforme seu domínio.
- Registre sempre a razão da decisão (debug) para monitorar e melhorar regras.

## Recursos futuros

- Integração com Gmail API (OAuth) para ingestão direta.
- Pipeline de OCR (reconhecimento óptico de caracteres) mais robusto para PDFs escaneados.
- Interface para rotulagem manual e re‑treino do modelo ML.

## Contribuição

Contribuições são bem‑vindas. Abra uma issue ou envie um pull request.

## Licença

Projeto licenciado sob MIT. (Adicione o arquivo LICENSE se desejar.)
