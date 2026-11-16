<img src=".claude-plugin/icon.png" width="96" alt="">

# next-task

[Read in English](README.md)

Una skill de agente para avanzar por un backlog **una tarea por sesión**. Usa el formato
abierto [Agent Skills](https://agentskills.io), así que funciona en Claude Code, Codex,
Gemini CLI, GitHub Copilot, Cursor y Devin Desktop (antes Windsurf). En cada
sesión toma la siguiente tarea y la lleva hasta un pull request verificado. Deja una línea
de traspaso en el repositorio y te pide que empieces una sesión nueva (`/clear`) y escribas `/next-task` otra vez.

Escribes dos comandos. Cada tarea gasta un 60 % menos de tokens, sin saltarse las pruebas
ni la revisión.

## Ahorro medido

Las cifras salen de 561 pull requests reales de dos proyectos en producción:

- [LK Creator](https://lkcreator.com), un SaaS en FastAPI y Next.js que convierte
  contenido personalizado de Minecraft.
- ISO 21101 turismo, una aplicación web de gestión de la seguridad para operadores de
  turismo de aventura.

Los datos son el uso de tokens que Claude Code ya guarda en las transcripciones locales de
cada sesión. Mismo desarrollador, mismo modelo (Claude Opus), noviembre de 2026. Las otras
herramientas no se midieron: la idea debería valer igual, porque todas releen la
conversación en cada paso, pero no tenemos cifras de ellas.

| | Una tarea por sesión | Tareas encadenadas (≥3 PR en una sesión) | Ahorro (IC 95 %) |
|---|---|---|---|
| Costo por PR, LK Creator | 4,39 USD (162 PR) | 14,58 USD (131 PR) | **70 %** (37–72 %) |
| Costo por PR, ISO 21101 turismo | 5,10 USD (49 PR) | 9,63 USD (219 PR) | **47 %** (18–78 %) |
| **Costo por PR, los dos** | | | **60 %** (42–74 %) |
| **Contexto por llamada al modelo, los dos** | 123–130k tokens | 342–357k tokens | **73 %** (62–75 %) |

**Con suscripción.** Leímos `/usage` tres veces, alrededor de dos periodos de trabajo, y
sumamos los tokens de todas las sesiones de ese tiempo, de todos los proyectos y con los
subagentes.

- Un punto del límite semanal costó 17,4 USD en tokens equivalentes de la API: 11 puntos
  en total, 0,059 y 0,057 puntos por dólar en los dos periodos.
- `/usage` redondea a puntos enteros, así que esta cifra tiene un margen de ±9 %.
- Con eso, una tarea por sesión gasta cerca del **0,25–0,29 % del límite semanal por
  PR**. Encadenando tareas se gasta un **0,55–0,84 %**. Es decir, unas **dos veces más PR
  por semana** con el mismo plan.

**Por qué funciona.** Cada llamada al modelo vuelve a leer toda la conversación. En una
sesión encadenada el contexto de cada llamada no para de crecer; pasó de 500k tokens
después de unas 10 tareas. Así, cada tarea paga por todas las anteriores. Una sesión nueva
empieza cada tarea con el mismo contexto pequeño.

### Calidad: no empeora, y los pasos de seguridad sí se hacen

Cruzamos los primeros 510 de estos PR con su historial de GitHub:

| | Una tarea por sesión | Encadenadas | Diferencia (IC 95 %) |
|---|---|---|---|
| Fusionados | 98,2 % | 98,6 % | ninguna (−3,5 a +3,1 pts) |
| Revertidos después | 0 % | 0 % | ninguna |
| Pruebas o typecheck antes de abrir el PR | **97,6 %** | 75,1 % | 22,5 pts más (2 a 38) |
| Revisión de código antes de abrir el PR | **87,9 %** | 14,8 % | 73 pts más (55 a 87) |

En las sesiones largas y encadenadas, el modelo empieza a saltarse sin avisar la
verificación y la revisión a medida que se llena el contexto. Una sesión nueva cumple la
lista completa casi siempre.

También medimos el «retrabajo en 7 días»: un PR `fix` posterior que toca los mismos
archivos de código. Favoreció a una tarea por sesión en ISO 21101 turismo (8,6 % frente a
59,2 %), pero tiene demasiado ruido para afirmarlo. En estos repositorios un tercio de los
PR son arreglos planeados sobre los mismos módulos, así que el intervalo combinado cruza
el cero.

### Pruebas de comportamiento

Antes de publicarla corrimos esta versión y la anterior en tres repositorios preparados,
calificados automáticamente (guiones en [`tests/`](tests/)):

- **primero un bug real:** lo arregla, y solo esa tarea;
- **primero una tarea ya resuelta:** comprueba la premisa, la marca como obsoleta y sigue
  con la siguiente;
- **sin backlog:** ofrece crearlo y no se inventa trabajo.

Esta versión pasó 19 de 19 comprobaciones con el mismo gasto de tokens que la anterior
(≈54k por corrida). La anterior escribía números de PR inventados en el traspaso cuando no
había remoto, y esta versión lo corrige.

### Cómo se midió

Los guiones están en [`bench/`](bench/).

- **Costo.** Tomamos los tokens de cada llamada al modelo, incluidos los subagentes, y los
  ponderamos con las proporciones de precio de Anthropic: lectura de caché 0,1×, escritura
  de caché 1,25× o 2×, salida 5×. Comparamos esos pesos con el costo que registra Claude
  Code y coinciden con un margen de ±10 %.
- **Tarea.** Una tarea es un pull request creado de verdad en esa sesión: un
  `gh pr create` que devolvió la URL del PR.
- **Intervalos de confianza.** Hicimos un bootstrap de 5.000 muestras por **sesiones**, no
  por tareas. Así una sesión larga no cuenta como 100 muestras independientes.

### Límites, dichos claramente

- Es un estudio observacional, no un experimento A/B. Las tareas de los dos grupos son
  distintas, y el grupo encadenado tiene solo 11 sesiones.
- Las cifras en dólares son equivalentes al precio de la API. La de la suscripción sale de
  dos periodos y hay que leerla como una estimación.
- La tabla de calidad muestra que las comprobaciones se *corrieron*. No puede mostrar que
  cada una se hizo bien.

### Mídelo en tus propias sesiones de Claude Code

```bash
python bench/measure.py ~/.claude/projects/<carpeta-de-tu-proyecto> next-task sessions.json
python bench/compare.py sessions.json
python bench/bootstrap.py "mio=sessions.json"
```

## Qué hace en cada sesión

0. **Guarda.**
   - Si en esta conversación ya cerró una tarea, te pide `/clear` primero.
   - Si uno de tus PR sigue abierto, termina ese primero.
   - Si el CI de la rama principal está en rojo, arreglarlo *es* la tarea.
1. **Elige.** Toma la primera tarea abierta del backlog (`BACKLOG.md`, `TODO.md` o los
   issues de GitHub) y lee solo la parte que necesita.
2. **Comprueba la premisa.** Confirma en el código que el problema sigue existiendo y
   descarta las tareas que ya están resueltas.
3. **La hace.** Busca la causa raíz y la arregla en el mecanismo compartido, con el estilo
   del código que la rodea.
4. **Verifica.** Corre las comprobaciones que correría el CI y después revisa el diff.
5. **Abre el PR.** Solo fusiona si el archivo de instrucciones del proyecto lo autoriza expresamente, y solo con las
   comprobaciones en verde.
6. **Deja el traspaso.** Escribe una línea en el backlog con el número del PR y lo único
   que la próxima sesión necesita saber.
7. **Para.** Te pide una sesión nueva (`/clear`) y después `/next-task`.

Sigue estas reglas de tokens todo el tiempo:

- el repositorio es la memoria;
- lee rangos de líneas, no archivos enteros;
- las búsquedas amplias van a un subagente que contesta en menos de 15 líneas;
- recorta la salida de cada comando;
- usa herramientas de línea de comandos antes que MCP;
- nunca vuelve a deducir algo que ya estableció;
- para después de dos intentos fallidos del mismo arreglo;
- si la conversación se compacta, lo toma como señal de que la tarea era demasiado grande.

Funciona sin remoto de GitHub. En ese caso hace el commit en una rama y te deja el PR a ti.

Te contesta en tu idioma; la skill está escrita en inglés porque es lo que lee el modelo.

## Instalación

**Claude Code, como plugin:**

```
/plugin marketplace add EliptikWu/next-task
/plugin install next-task@eliptikwu
```

O copia `skills/next-task/` en `~/.claude/skills/next-task/` (todos los proyectos) o en
`<repo>/.claude/skills/next-task/` (uno solo).

**Otras herramientas:** copia `skills/next-task/` en `<repo>/.agents/skills/next-task/`
para un proyecto, o en `~/.agents/skills/next-task/` para todos. Todas las de la tabla
leen esa carpeta.

| Herramienta | Cómo se usa | Sesión nueva |
|---|---|---|
| Codex | `$next-task` | `/new` |
| Gemini CLI | dile «next task» o «siguiente» (elige la skill sola) | `/clear` |
| GitHub Copilot en VS Code | `/next-task` | New Chat (Ctrl+N) |
| GitHub Copilot CLI | `/next-task` | `/clear` |
| Cursor | `/next-task` | New chat (Cmd/Ctrl+N) |
| Devin Desktop (antes Windsurf) | `/next-task` | una conversación nueva |

Las instrucciones del proyecto van en el archivo que lea tu herramienta (`CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`...). La skill sigue ese archivo.

Si un proyecto ya tiene su propia skill para este ciclo, gana la del proyecto.

¿Todavía no tienes backlog? La skill ofrece crearlo. El formato está en
[`skills/next-task/reference/backlog-format.md`](skills/next-task/reference/backlog-format.md).

## Licencia

[Apache 2.0](LICENSE). Puedes usarla, cambiarla y compartirla. Las copias y las versiones
derivadas deben conservar el aviso de autoría y el archivo [NOTICE](NOTICE), y decir qué
se cambió. La licencia no da derecho a usar el nombre del autor para promocionar una
versión derivada.

Hecho por [EliptikWu](https://github.com/EliptikWu) en LK Industries.
