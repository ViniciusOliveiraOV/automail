describe('Classify page', () => {
  beforeEach(() => {
    cy.visit('http://127.0.0.1:5000/');
  });

  it('submits text and shows score panel', () => {
    cy.get('textarea[name="text"]').clear().type('This is a short productive email about a meeting and action items.');
    cy.get('button[type="submit"]').click();

    cy.url().should('include', '/classify');
    cy.get('.score-panel').should('exist');
    cy.get('.score-card').should('have.length.at.least', 1);
    cy.contains('Produtivo').should('exist');
  });
});
