# /impact - Analise de impacto antes de mudanca

## Objetivo

Padronizar analise de risco antes de alterar funcoes, modulos ou contratos de dados.

## Formato obrigatorio

```text
impact(target: "<funcao/modulo>")
-> direct callers: WILL BREAK | SAFE
-> indirect callers: LIKELY AFFECTED | LOW RISK
-> flows afetados: <lista de fluxos>
-> arquivos de teste a executar: <lista>
-> docs a atualizar: <lista>
-> risco: HIGH | MEDIUM | LOW
```

## Regras

1. Sempre incluir pelo menos um teste candidato.
2. Sempre incluir ao menos uma doc impactada quando mudar comportamento.
3. Em risco HIGH, pedir validacao humana antes de merge.
