Testes Cypress (E2E)

Pré‑requisitos

1. Instale o Node (>=16) e o npm.
2. A partir da raiz do projeto execute:

   npm install

Executar a aplicação

1. Inicie a aplicação Flask em um terminal separado:

   # PowerShell (Windows)
   $env:FLASK_APP = 'app'; flask run --host 127.0.0.1 --port 5000

Executar o Cypress

Abrir o runner interativo:

   npm run cypress:open

Executar em modo headless:

   npm run cypress:run

Observações

- Os testes esperam que o servidor de desenvolvimento esteja acessível em http://127.0.0.1:5000.
- Se sua aplicação Flask estiver em outra porta/host, altere `baseUrl` em `cypress.config.js`.
- O arquivo de teste `cypress/e2e/classify_spec.cy.js` faz um POST simples pela UI e verifica a presença do fragmento `.score-panel`.

Caso seja necessário expor o servidor para acesso remoto, use sua ferramenta de tunelamento preferida.
