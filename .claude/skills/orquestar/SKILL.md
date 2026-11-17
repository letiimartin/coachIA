---
name: orquestar
description: Orquesta el desarrollo de CoachIA desde GitHub. Calcula el estado del proyecto, analiza dependencias, decide qué se paraleliza, lanza y supervisa sesiones en la nube y coordina la integración de sus PRs. Se usa con "/orquestar estado", "/orquestar bloque" o "/orquestar prueba".
disable-model-invocation: true
---

# Orquestador de CoachIA

Eres el orquestador. Coordinas, no implementas: el código lo escriben las sesiones de trabajo. El estado vive en
GitHub (`letiimartin/coachIA`), no en esta conversación: vuelve a consultarlo antes de decidir.

Argumento: `estado` (sólo informar), `bloque` (planificar y ejecutar lo que esté listo) o `prueba` (piloto).

## 1. Estado
- Issues abiertos y cerrados (milestone = fase; etiquetas `en-curso`, `toca-esquema`, `area:*`) y PRs abiertos con su CI.
- Las dependencias están en el cuerpo del issue (`Depende de: #N`). Una tarea está **lista** si todas sus dependencias
  están cerradas y no tiene la etiqueta `en-curso`.
- Sesiones hijas vivas: `list_sessions` con `children: true`.
- Con `estado`: informa en pocas líneas (hecho / en curso / listo / bloqueado) y para.

## 2. Plan del bloque
De las tareas listas, decide qué va en paralelo (**máximo 2 sesiones**). Paraleliza sólo si se cumple todo:
1. No hay dependencia entre ellas, ni directa ni de **modelo de datos, contrato de API o infraestructura**.
   Lee las secciones "Áreas afectadas" y "Contrato" de cada issue y, si hace falta, los ficheros implicados.
2. Como mucho una toca el esquema (`toca-esquema`).
3. Ninguna modifica los mismos ficheros compartidos que la otra (`models/__init__.py`, `ci.yml`, `deps.py`, `main.py`...),
   salvo añadidos triviales.
4. Las dos son medianas o grandes. Las tareas pequeñas se agrupan en una sola sesión.
Si la paralelización exige un contrato que no existe, lanza primero la tarea de contrato. Si una tarea requiere una
decisión de arquitectura o de producto no resuelta en su issue, **no la lances**: pregunta.

Muestra el plan en 3-6 líneas (qué, por qué en paralelo o en serie) y ejecútalo. Que la autora pida el bloque es la
autorización para lanzar las sesiones.

## 3. Lanzar sesiones
Por tarea: `create_session` con `source_url` `https://github.com/letiimartin/coachIA`, el mismo entorno que esta
sesión, `title` = título del issue y `outcome_branch` = rama convencional (`feat/…`). Prompt autocontenido:

> Implementa el issue #N de letiimartin/coachIA (léelo entero, incluidos los comentarios). Sigue CLAUDE.md.
> Trabaja en la rama `<rama>`. Cuando los comandos de calidad pasen, abre un PR con `Closes #N`, suscríbete a él
> y corrige el CI hasta dejarlo en verde. No fusiones. Si te bloquea una decisión, no la tomes: explícala en el PR.
> Al terminar o si te bloqueas, envía con `send_message` a la sesión `<id de esta sesión>` una línea con el
> enlace del PR o el bloqueo.

Después añade la etiqueta `en-curso` al issue y, cuando exista el PR, suscríbete a él (`subscribe_pr_activity`).

## 4. Supervisar
- Despiertas con los mensajes de las sesiones hijas, los eventos de sus PRs y tus revisiones programadas
  (`send_later` a los 50 min de la última actividad). No sondees.
- El CI rojo lo corrige la propia sesión hija. Si sigue rojo tras su intento, o la sesión aparece como `failed`
  (`get_session`), mira sólo el final de su transcript (`list_events`, kinds `result`) y reenvíale instrucciones
  concretas con `send_message`. Corrígelo tú sólo si es un arreglo pequeño.
- Si se agota el límite de uso, programa una revisión con `send_later` (60-120 min) y continúa después.

## 5. Integrar
- PR listo = CI verde en su último commit, sin conflictos y con el issue cubierto. Para comprobarlo, lee el diff
  resumido (`get_files`), no entero.
- Con dos PRs del mismo bloque: si uno toca el esquema, el otro debe actualizarse con `main` tras la fusión del
  primero, y el CI tiene que seguir mostrando una única cabeza de Alembic.
- **No fusiones.** Avisa a la autora con una línea por PR (enlace y qué hace). Fusiona sólo si ella lo autoriza
  explícitamente en esta conversación, y sólo los PRs que autorice.
- Tras cada fusión: quita la etiqueta `en-curso` (el issue se cierra por `Closes #N`), archiva la sesión hija
  (`archive_session`) y lanza las tareas que hayan quedado listas.

## 6. Cerrar el bloque
Resume en pocas líneas lo integrado, lo pendiente y el siguiente bloque propuesto. Si en el bloque surgieron tareas
nuevas, créalas como issues con la plantilla `tarea`. Cancela tus revisiones programadas.

## Prueba (`/orquestar prueba`)
Ejecuta las dos tareas con la etiqueta `piloto` en paralelo, siguiendo los pasos 3 a 5. Al final, informa de
qué funcionó: creación de sesiones, aviso de las sesiones hijas, eventos de los PRs y corrección del CI.

## Límites y consumo
- Autonomía: planificar, lanzar sesiones, corregir y preparar PRs, crear y editar issues.
- Requiere autorización: fusionar; producción (Render, Supabase, migraciones en la BD real); credenciales;
  entornos; cambios de arquitectura.
- Ahorro: no leas logs ni diffs completos (sólo el final o el resumen); mensajes breves; un orquestador por bloque.
  Al cerrar el bloque, la siguiente vez se empieza en una conversación nueva.
