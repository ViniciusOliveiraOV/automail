Cypress E2E tests

Setup

1. Install node (>=16) and npm.
2. From the project root run:

   npm install

Run the app

1. Start the Flask app in a separate terminal:

   # Windows PowerShell
   $env:FLASK_APP = 'app'; flask run --host 127.0.0.1 --port 5000

Run Cypress

Open interactive runner:

   npm run cypress:open

Run headless:

   npm run cypress:run

Notes

- The tests expect the dev server to be reachable at http://127.0.0.1:5000.
- If your Flask app runs under a different port or host, change `baseUrl` in `cypress.config.js`.
- The test file `cypress/e2e/classify_spec.cy.js` performs a simple POST via the UI and checks for the `.score-panel` fragment.

Note: the tests assume the dev server is reachable locally at http://127.0.0.1:5000; use your preferred tunneling tool if remote access is required.
