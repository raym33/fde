# GOBIERNO MINIMO VIABLE DE IA — BASE

## Naturaleza de la nota

Marco base para que VirtuDirector IA no recomiende automatizaciones sin un
suelo minimo de control, especialmente en pymes que empiezan a usar IA.

## Controles minimos

- politica de uso de IA,
- inventario de herramientas IA activas,
- clasificacion de datos sensibles,
- permisos por usuario o rol,
- logs de acciones y revisiones,
- aprobacion humana en tareas de riesgo,
- criterio para usar local vs cloud,
- plan de rollback si un workflow falla.

## Regla por nivel de riesgo

- Bajo: FAQ, resumenes, clasificacion simple.
- Medio: borradores operativos, scoring interno, automatizaciones con revision.
- Alto: salud, credito, seleccion, decisiones legales, biometria o tramites
  sensibles. Aqui siempre debe haber supervisión humana y control reforzado.

## Señales de mala gobernanza

- cada empleado usa una IA distinta,
- no se sabe que datos salen a proveedores,
- se pegan contratos o historias clinicas en cloud,
- no hay trazas de por que se genero una respuesta,
- el negocio no sabe desactivar una automatizacion rapido.

## Salida minima que la app deberia generar

- semaforo de riesgo,
- recomendacion local/cloud/hibrida,
- checklist de controles faltantes,
- politica corta de uso IA adaptable,
- decision sobre que no debe automatizarse todavia.

## Texto compacto para guardar

`Gobierno minimo viable: inventario de herramientas IA, clasificacion de datos,
permisos, logs, aprobacion humana y rollback. Sin esto, no hay despliegue serio,
solo riesgo oculto.`
