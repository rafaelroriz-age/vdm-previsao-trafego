"""
formulas.py
-----------
Conversores da string de equação do pipeline para LaTeX e Excel,
permitindo que engenheiros calculem as previsões fora do ambiente de dados.

Portado de `vdm-regressao-previsto/pipeline.py`.
"""
from __future__ import annotations

import re


def equation_to_latex(eq_str: str) -> str:
    """Converte a equação em LaTeX multilinha (uma linha por termo)."""
    lines = eq_str.strip().split("\n")
    latex_lines = []
    for line in lines:
        line = line.strip()
        if not line or "Duan smearing" in line or "exp(log" in line:
            continue
        line = re.sub(r"ŷ\(([^)]+)\)", r"\\hat{y}_{\\text{\1}}", line)
        line = re.sub(r"log\(ŷ\(([^)]+)\)\)", r"\\log(\\hat{y}_{\\text{\1}})", line)
        line = line.replace(" × ", " \\times ")
        line = re.sub(r"(?<!\\)_", r"\\_", line)
        latex_lines.append(f"${line}$")
    return "\n\\\\\n".join(latex_lines)


def equation_to_latex_inline(eq_str: str) -> str:
    """Converte a equação em uma única linha LaTeX (para renderização inline)."""
    lines = eq_str.strip().split("\n")
    parts = []
    for line in lines:
        line = line.strip()
        if not line or "Duan smearing" in line or "exp(log" in line:
            continue
        if " = " in line and not parts:
            lhs, rhs = line.split(" = ", 1)
            lhs = re.sub(r"ŷ\(([^)]+)\)", r"\\hat{y}_{\\text{\1}}", lhs)
            lhs = re.sub(r"log\(ŷ\(([^)]+)\)\)", r"\\log(\\hat{y}_{\\text{\1}})", lhs)
            parts.append(lhs + " =")
            m = re.match(r"([+-]?\s*[\d.]+)", rhs)
            if m:
                parts.append(m.group(1).replace(" ", ""))
            continue
        m = re.match(r"([+-])\s+([\d.]+)\s+\S\s+(.+)", line)
        if m:
            sign, coef, feature = m.group(1), m.group(2), m.group(3).strip()
            feature_escaped = feature.replace("_", "\\_")
            parts.append(f"{sign} {coef} \\times \\text{{{feature_escaped}}}")
    return " ".join(parts)


def equation_to_excel(eq_str: str) -> str:
    """Converte a equação em fórmula Excel (formato PT-BR, vírgula decimal)."""
    lines = eq_str.strip().split("\n")
    intercept = None
    terms = []
    for line in lines:
        line = line.strip()
        if not line or "Duan smearing" in line or "exp(log" in line:
            continue
        if " = " in line and intercept is None:
            rhs = line.split(" = ", 1)[1]
            match = re.match(r"([+-]?\s*[\d.]+)", rhs)
            if match:
                intercept = float(match.group(1).replace(" ", ""))
            continue
        match = re.match(r"([+-])\s+([\d.]+)\s+\S\s+(.+)", line)
        if match:
            terms.append((match.group(1), float(match.group(2)), match.group(3).strip()))
    if intercept is None:
        return ""

    def ptbr(n):
        return f"{n:.4f}".replace(".", ",")

    formula = f"={ptbr(intercept)}"
    for sign, coef, feature in terms:
        formula += f" {sign} {ptbr(coef)}*{feature}"
    return formula
