# STACK Y RUNTIME LOCAL — 2026-05-21

## Naturaleza de la nota

Resumen técnico-comercial para alimentar los módulos `Runtime local`,
`Solución low-cost` y `Diagnóstico de oportunidades`.

## Stack recomendado para pymes

### Opción A: Local soberano

- Componentes: `Ollama` o `LM Studio`, embeddings locales, RAG local, `n8n`,
  parser PDF/DOCX, logs.
- Mejor para: clínicas, despachos, asesorías, ayuntamientos, departamentos con
  contratos/facturas/expedientes.
- Ventaja: privacidad, coste de API casi cero, control de datos.
- Límite: rendimiento y tool calling pueden requerir ajuste; no prometerlo para
  razonamiento crítico sin fallback.

### Opción B: Híbrido low-cost

- Componentes: `n8n`, `Make`, ChatGPT/Claude/Gemini, RAG interno, revisión
  humana.
- Mejor para: procesos de baja sensibilidad, prototipos rápidos, marketing,
  borradores y atención al cliente no sensible.
- Ventaja: rapidez y calidad lingüística.
- Límite: coste variable y riesgo de exposición si no hay política clara.

### Opción C: Local-first con escalado premium

- Componentes: modelos locales para triaje/resumen/RAG; modelo frontera solo
  para síntesis estratégica o GRC.
- Mejor para: VirtuDirector IA como producto CAIO.
- Ventaja: equilibrio entre coste, privacidad y calidad.
- Límite: necesita router de modelos, observabilidad y umbrales de escalado.

## Señales técnicas del día

- LM Studio beta con MTP: posible mejora de velocidad local.
- Ollama sigue siendo vía práctica para validar modelos antes de pagar APIs.
- RAG local con 600-800 EUR es viable si el caso es documental y acotado.
- n8n es el orquestador low-code dominante para quick wins.
- Make/ChatGPT Pro pueden servir para pilotos de baja sensibilidad, pero se debe
  medir coste real por tarea.

## Reglas de decisión para VirtuDirector IA

- Si hay datos sensibles: preferir local o local-first.
- Si el proceso es repetitivo y textual: empezar con n8n + RAG/FAQ.
- Si hay necesidad de razonamiento estratégico: escalar solo esa parte a modelo
  premium.
- Si el cliente no tiene base digital: diagnosticar primero, no automatizar.
- Si no hay trazas: no desplegar en producción.

## Texto compacto para guardar

`Stack 2026 para pymes: n8n + Ollama/LM Studio + RAG local como base soberana;
cloud solo cuando aporte razonamiento extra o velocidad de prototipo. Regla:
datos sensibles local, tareas repetitivas automatizables, humano revisa lo
crítico.`
