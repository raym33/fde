"""Redacción ligera de PII antes de enviar texto a modelos externos.

MVP basado en regex para los patrones más comunes en la UE (email, teléfono,
IBAN, DNI/NIE español, tarjetas). En producción, sustituir/combinar con un
motor dedicado (p. ej. Presidio) y reglas por idioma/país. La redacción es
reversible mediante el mapa devuelto, para rehidratar la respuesta si procede.
"""
from __future__ import annotations

import re

_PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[ -]?)?(?:\d[ -]?){9,12}\b"),
    "DNI": re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"),
    "NIE": re.compile(r"\b[XYZ]\d{7}[A-HJ-NP-TV-Z]\b"),
}


def redact(text: str) -> tuple[str, dict[str, str]]:
    """Devuelve (texto_redactado, mapa_placeholder->original)."""
    mapping: dict[str, str] = {}
    counter: dict[str, int] = {}
    out = text
    for label, pattern in _PATTERNS.items():
        for match in pattern.findall(out):
            value = match if isinstance(match, str) else match[0]
            if not value or value in mapping.values():
                continue
            counter[label] = counter.get(label, 0) + 1
            placeholder = f"[{label}_{counter[label]}]"
            mapping[placeholder] = value
            out = out.replace(value, placeholder)
    return out, mapping


def rehydrate(text: str, mapping: dict[str, str]) -> str:
    for placeholder, value in mapping.items():
        text = text.replace(placeholder, value)
    return text
