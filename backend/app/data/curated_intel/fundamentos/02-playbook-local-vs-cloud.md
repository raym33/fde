# PLAYBOOK LOCAL VS CLOUD — BASE

## Naturaleza de la nota

Reglas de decision evergreen para responder a la pregunta mas repetida en
VirtuDirector IA: cuando conviene usar IA local, cloud o un enfoque hibrido.

## Regla rapida

- Datos sensibles o confidenciales: priorizar local o local-first.
- Volumen bajo y consultas documentales: local suele ser viable.
- Necesidad de razonamiento complejo o calidad premium: hibrido.
- Prototipo urgente y baja sensibilidad: cloud puede acelerar.

## Cuando recomendar local

- fichas medicas, contratos, expedientes, facturas,
- consultas internas sobre documentos,
- empresas que quieren coste fijo y privacidad fuerte,
- equipos que pueden operar un runtime sencillo tipo Ollama o LM Studio.

## Cuando recomendar cloud

- borradores de marketing o ventas no sensibles,
- analisis exploratorio rapido,
- tareas donde la calidad de redaccion pesa mas que la soberania,
- equipos sin capacidad minima de operar nada local.

## Cuando recomendar hibrido

- triaje, extraccion, FAQ y RAG en local,
- sintesis ejecutiva o casos complejos en modelo premium,
- workflows donde una parte necesita privacidad y otra solo mejor lenguaje.

## Variables que cambian la decision

- sensibilidad de datos,
- consultas por dia,
- latencia aceptable,
- presupuesto mensual,
- necesidad de tool calling,
- capacidad del equipo para operar infraestructura minima.

## Errores comunes

- creer que local siempre es mas barato aunque el equipo no pueda operarlo,
- creer que cloud siempre es mejor porque responde bonito,
- olvidar permisos y trazabilidad del indice RAG,
- mezclar documentos sensibles con prompts externos por comodidad.

## Respuesta corta que la app deberia poder dar

`Si manejas datos sensibles o quieres coste fijo, empieza por local. Si necesitas
calidad premium en una parte del flujo, usa hibrido. Si el caso no es sensible y
necesitas velocidad de prototipo, cloud puede servir para validar antes.`
