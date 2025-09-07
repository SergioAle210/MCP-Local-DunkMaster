# Prompts (Natural Language) — DunkMaster Stats MCP

These prompts assume your chatbot routes natural language to MCP tools.

> Tip: After each action, ask your host to **print the tool output** (the server returns pretty JSON as text).
> If your host keeps an MCP log (JSONL), show a tail to evidence `initialize`, `list_tools` and `call_tool` exchanges.

---

## Player summaries

1. Muéstrame el **resumen de carrera** de **Michael Jordan**.
2. ¿Cuál es el **span de carrera** y los **equipos** de **Kobe Bryant**?
3. Dame los **promedios de carrera** (PTS/AST/TRB) de **Tim Duncan**.
4. ¿Cuántas **selecciones al All‑Star** tiene **LeBron James**?

## Top scorers by season

5. Top **10** anotadores de la temporada **1996**.
6. Top **5** anotadores de **2016**.
7. Top **15** anotadores de **1988**.

## Player comparisons

8. Compara **Michael Jordan** vs **LeBron James** por **per_game**.
9. Compara **Stephen Curry** vs **Damian Lillard** por **per_36**.
10. Compara **Larry Bird** vs **Magic Johnson** por **per_100**.

## Team summaries

11. Resumen de **Chicago Bulls** en **1996** (SRS, ORtg, DRtg, pace, W‑L).
12. Resumen de **Miami Heat** en **2013**.
13. Resumen de **San Antonio Spurs** en **2007**.

---

## Bonus (for orchestrators mixing tools)

14. Agrega al archivo `report.md` una **sección** con el resumen de **Michael Jordan** y haz **commit** con el mensaje `docs: add MJ summary`.
15. Compara **Jordan** vs **LeBron** por **per_36** y **guarda** el resultado en `comparisons/mj_lb.json`.

> (Los puntos 14–15 requieren que tu host también integre Filesystem MCP y Git MCP.)

---

## What to expect

- The server returns a **single text block** with **pretty JSON** (no binary content).
- Names are matched **fuzzily**; si la coincidencia no es la esperada, prueba con el nombre completo correcto.
- Seasons are **integers** (e.g., `1996`).

Happy querying 🏀
