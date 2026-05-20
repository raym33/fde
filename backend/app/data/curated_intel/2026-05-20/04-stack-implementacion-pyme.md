# STACK MAS USADO EN IMPLEMENTACIONES IA DE PYME — 2026-05-20

## Naturaleza de la nota

Sintesis curada de lo que aparece como stack mas repetido en implementaciones
practicas de IA para pymes, segun notas de operador y resumenes recientes.

## Stack dominante

El stack que mas se repite para pymes en 2026 es:

- `n8n` para orquestacion y automatizacion.
- `Ollama` como runtime local principal.
- `Qdrant` o `Chroma` para almacenamiento vectorial ligero.
- `RAG` con documentos internos y permisos claros.
- `Claude`, `Gemini` o `GPT-4o` solo para tareas puntuales de razonamiento
  superior cuando el caso lo exige.

## Por que gana

- Coste muy contenido frente a varias SaaS aisladas.
- Mejor historia de privacidad y soberania de datos.
- Rapido de montar para quick wins.
- Encaja bien con entornos mixtos: local para lo sensible, cloud para lo
  complejo.

## Modelos y runtimes mas repetidos

- `Ollama`: base de muchos despliegues locales.
- `LM Studio`: alternativa comoda en escritorio y Apple Silicon.
- `Qwen`, `Gemma`, `Llama`, `Mistral`: modelos frecuentes para inferencia local.
- `Claude`: muy citado para coding, razonamiento y orquestacion compleja.

## Repos y frameworks frecuentes

- `n8n`
- `Ollama`
- `LangChain` / `LangGraph`
- `LlamaIndex`
- `Dify`
- starter kits de self-hosting con `n8n + Ollama + Qdrant`

## Uso recomendado en VirtuDirector IA

- `Solucion low-cost`: n8n + Ollama como opcion por defecto para quick wins.
- `Runtime local`: LM Studio/Ollama para privacidad y control de coste.
- `RAG cliente`: copilotos privados sobre documentos internos.
- `Roadmap 90 dias`: decision explicita entre local, cloud o hibrido segun
  sensibilidad del dato, volumen y ROI esperado.

Texto compacto:

`Stack dominante pyme 2026: n8n + Ollama + RAG con vector DB ligera. Cloud solo
cuando hace falta mas razonamiento. La decision ya no es 'usar IA o no', sino
'que parte corre local y que parte merece cloud'.`

