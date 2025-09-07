# DunkMaster Stats MCP (Local)

An **MCP server** that exposes _non‑trivial_ NBA analytics over **22 CSV datasets (1947–present)**.  
Transport: **STDIO** (local). Designed to be consumed by any MCP host/chatbot that can spawn a local server and call MCP tools.

> This repository is intended for the “local MCP server” requirement in your networking/LLM project.
> It loads the CSVs once on startup and offers four tools: `player_summary`, `top_scorers`, `compare_players`, `team_summary`.

---

## Contents

- [Features](#features)
- [Tools (Endpoints)](#tools-endpoints)
- [Installation](#installation)
- [Data layout (required CSVs)](#data-layout-required-csvs)
- [Quick start (diagnostic run)](#quick-start-diagnostic-run)
- [Integrating with your chatbot](#integrating-with-your-chatbot)
  - [A) Environment‑variable setup](#a-environment-variable-setup)
  - [B) Spawning the server (STDIO)](#b-spawning-the-server-stdio)
  - [C) Calling tools](#c-calling-tools)
- [Natural‑language prompts to test](#natural-language-prompts-to-test)
- [Troubleshooting](#troubleshooting)
- [License & Data credit](#license--data-credit)

---

## Features

- **Local, offline analytics**: no external API calls; your host only needs to spawn one process via STDIO.
- **Fast CSV engine** with `pandas`, preloaded once on startup.
- **Fuzzy player/team matching** via `rapidfuzz` (handles minor typos).
- **Deterministic JSON output** (pretty‑printed text) – easy to render or post‑process.
- **Version‑tolerant server boot**: works with `FastMCP` variants that expose either `run()` or `run_stdio()`.

---

## Tools (Endpoints)

All tools are reachable via MCP **`call_tool`**. Request/response bodies are JSON. The server returns a single **text part** containing **pretty JSON**.

### `player_summary(player: string) -> object`

Returns:

```json
{
  "match": "Michael Jordan",
  "score": 99.0,
  "span": { "from": 1985, "to": 2003 },
  "teams": ["CHI", "WAS"],
  "career_avgs": { "pts": 30.12, "ast": 5.3, "trb": 6.2 },
  "all_star_selections": 14,
  "top_award_shares": [
    { "award": "MVP", "season": 1996, "share": 0.97, "winner": true }
  ]
}
```

Notes: Weighted career averages by games when possible; fuzzy name resolution.

### `top_scorers(season: int, n: int = 10) -> array<object>`

Returns top _n_ by **PTS/G** for the season:

```json
[
  { "player": "Michael Jordan", "team": "CHI", "pts_per_game": 30.4, "g": 82 },
  { "player": "Hakeem Olajuwon", "team": "HOU", "pts_per_game": 27.3, "g": 82 }
]
```

### `compare_players(player_a: string, player_b: string, basis: "per_game"|"per_36"|"per_100" = "per_game") -> object`

Returns side‑by‑side weighted career averages for the chosen basis:

```json
{
  "basis": "per_36",
  "player_a": {
    "match": "Michael Jordan",
    "g": 1072,
    "pts": 28.3,
    "ast": 4.9,
    "trb": 5.9,
    "score": 99.0
  },
  "player_b": {
    "match": "LeBron James",
    "g": 1500,
    "pts": 26.6,
    "ast": 6.9,
    "trb": 7.2,
    "score": 99.0
  }
}
```

### `team_summary(season: int, team: string) -> object`

Returns record and efficiency metrics from _Team Summaries_ for that season:

```json
{
  "match": "Chicago Bulls",
  "score": 98.0,
  "season": 1996,
  "summary": {
    "w": 72,
    "l": 10,
    "srs": 11.8,
    "o_rtg": 115.2,
    "d_rtg": 101.8,
    "n_rtg": 13.4,
    "pace": 91.1
  }
}
```

---

## Installation

> **Python 3.10+** is recommended.

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install server dependencies
pip install -r requirements.txt
```

`requirements.txt` (reference):

```
mcp>=1.10.0
pandas>=2.2.0
python-dateutil>=2.9.0
rapidfuzz>=3.9.0
```

---

## Data layout (required CSVs)

Place **all 22 CSV files** under `./data/` with **exact** names (case‑sensitive on Linux/macOS). This server expects (subset shown):

```
Advanced.csv
All-Star Selections.csv
Draft Pick History.csv
End of Season Teams (Voting).csv
End of Season Teams.csv
Opponent Stats Per 100 Poss.csv
Opponent Stats Per Game.csv
Opponent Totals.csv
Per 100 Poss.csv
Per 36 Minutes.csv
Player Award Shares.csv
Player Career Info.csv
Player Per Game.csv
Player Play By Play.csv
Player Season Info.csv
Player Shooting.csv
Player Totals.csv
Team Abbrev.csv
Team Stats Per 100 Poss.csv
Team Stats Per Game.csv
Team Summaries.csv
Team Totals.csv
```

> **Minimum required by current tools:**  
> `Player Per Game.csv`, `Per 36 Minutes.csv`, `Per 100 Poss.csv`, `Player Totals.csv`, `Player Career Info.csv`, `All-Star Selections.csv`, `Player Award Shares.csv`, `Team Summaries.csv`.

---

## Quick start (diagnostic run)

You normally **don’t** run the server manually – your chatbot/host will spawn it via **STDIO**.  
For a quick diagnostic (to confirm the CSVs load without crashing):

```bash
python server.py --data ./data
# The process will keep running, waiting for STDIO (press Ctrl+C to stop)
```

If your installed `FastMCP` exposes `run_stdio()`, the server will use it; otherwise it will fall back to `run()` automatically.

---

## Integrating with your chatbot

Your host must be able to **spawn a local MCP server via STDIO**, then call MCP **tools**.

### A) Environment‑variable setup

Point your chatbot to this server script and to your data folder (adjust paths for your machine). On Windows with spaces in paths, prefer **forward slashes** and **no quotes**:

```
STATS_MCP_PATH=C:/path/to/MCP-Local-DunkMaster/server.py
STATS_DATA_PATH=C:/path/to/MCP-Local-DunkMaster/data
```

> If your host uses a `.env` loader (e.g., `python-dotenv`), put them there.  
> Keep values **without quotes** to avoid spawning errors on Windows.

### B) Spawning the server (STDIO)

- Use the **same Python interpreter** as your host (e.g., `sys.executable`) so the server sees the same site‑packages (pandas, mcp, rapidfuzz).
- Spawn command:  
  `command = sys.executable`  
  `args    = [STATS_MCP_PATH, "--data", STATS_DATA_PATH]`
- The host should then open a **stdio session** to speak MCP JSON‑RPC with the process.

**Pseudocode (host side):**

```python
import os, sys
from mcp.client.stdio import stdio_client
from mcp import ClientSession  # or equivalent in your MCP client lib

STATS_MCP_PATH = os.getenv("STATS_MCP_PATH")
STATS_DATA_PATH = os.getenv("STATS_DATA_PATH")

async with stdio_client(command=sys.executable,
                        args=[STATS_MCP_PATH, "--data", STATS_DATA_PATH]) as (read, write):
    session = ClientSession(read, write)
    await session.initialize()
    tools = await session.list_tools()      # should include player_summary, top_scorers, etc.
    # Call a tool:
    resp = await session.call_tool("player_summary", {"player": "Michael Jordan"})
    print(resp.content[0].text)             # pretty JSON string
```

> API names may vary slightly by MCP client library version. Any MCP‑capable host should follow the same pattern: **spawn stdio → initialize → list_tools → call_tool**.

### C) Calling tools

- **Tool names**: `player_summary`, `top_scorers`, `compare_players`, `team_summary`
- **Payload** is a JSON object with the parameters documented above.
- **Response** returns a single text block containing pretty JSON. Parse or just print it.

---

## Natural‑language prompts to test

You can route natural language to these tools from your chatbot’s planner/orchestrator. Examples:

1. “Muéstrame el **resumen de carrera** de **Michael Jordan**.” → `player_summary`
2. “Top **10 anotadores** de **1996**.” → `top_scorers(season=1996, n=10)`
3. “Compara **Michael Jordan** vs **LeBron James** por **per_36**.” → `compare_players(basis="per_36")`
4. “Dame un **resumen de equipo** de **Chicago Bulls** en **1996**.” → `team_summary`
5. “¿Cuántas **selecciones al All‑Star** tiene **Kobe Bryant**?” → `player_summary`
6. “Ordena a los **5 mejores anotadores** de **2016**.” → `top_scorers(season=2016, n=5)`
7. “Compara **Stephen Curry** vs **Damian Lillard** por **per_100**.” → `compare_players`
8. “Resumen de **Los Angeles Lakers** en **2001**.” → `team_summary`
9. “Resumen de **Tim Duncan** (equipos, span, promedios).” → `player_summary`
10. “Top **15** anotadores de **1988**.” → `top_scorers`
11. “Compara **Larry Bird** vs **Magic Johnson** (per_game).” → `compare_players`
12. “Dame el SRS y net rating de **Miami Heat** en **2013**.” → `team_summary`

---

## Troubleshooting

- **`FileNotFoundError: Missing CSV`**  
  Verify that file names are **exact** and placed under `./data/`. On Linux/macOS the filesystem is _case‑sensitive_.

- **Host “does not connect” / process exits immediately**

  - Use **`sys.executable`** to spawn the server with the **same venv** as your host.
  - Install the dependencies in that venv: `pip install -r <repo>/requirements.txt`.
  - On Windows, **do not add quotes** around `STATS_MCP_PATH` / `STATS_DATA_PATH`.
  - Prefer **forward slashes** for paths that contain spaces.

- **`AttributeError: 'FastMCP' has no attribute 'run_stdio'`**  
  Your `fastmcp` version does not expose that method. This server auto‑detects and falls back to `run()`.

- **Unexpected player/team matches**  
  Fuzzy matching is used. Try the exact name or refine the query; if your host supports it, add a disambiguation step.

---

## License & Data credit

- **Code**: MIT License (see `LICENSE`).
- **Data**: public basketball datasets consolidated from KP/BBRef (see original Kaggle source you used in your class).  
  Dataset reference used by students: <https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats>.

---

Happy hacking! 🏀
