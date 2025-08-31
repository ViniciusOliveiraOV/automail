# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

## Unreleased

- Removido endpoint de debug temporário `/_debug_llm_config` para adequação à produção.
- Preservadas as classes HTML do classificador durante a sanitização para permitir estilização dos fragmentos de score.
- Corrigidos estilos de heading e score; o fragmento do score agora é estilável e legível.
- Adicionado pipeline local de build do Tailwind e sobrescritas de CSS do projeto.
- Atualizado o spec do Cypress para tolerar múltiplos nomes de textarea e executar E2E em modo headless no CI.
- Diversos: pequenos bugs corrigidos e melhorias em testes (unitários + e2e passam localmente).

## Histórico anterior

- O baseline inicial do projeto e releases anteriores estão documentados no histórico de commits.

