# /validate - Validar documento

## Quando usar

Antes de marcar um documento como `validated`.

## Passos

1. Confirmar frontmatter com campos obrigatorios.
2. Verificar bloco `ai-summary` valido e objetivo.
3. Checar se todos os caminhos em `related` existem.
4. Revisar se ha evidencia no codigo para afirmacoes tecnicas.
5. Calcular confidence pela rubrica em `docs/CONVENTIONS.md`.
6. Se houver lacuna, manter `status: draft` ou `status: review`.

## Saida esperada

- Lista de problemas (ou "OK").
- Confidence proposto.
- Recomendacao de proxima acao.
