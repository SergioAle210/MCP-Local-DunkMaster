# MCP‑Local‑DunkMaster — NBA Stats MCP (Two integration modes)

This repository provides a **Model Context Protocol (MCP)** server over your local NBA datasets (22 CSVs, 1947–present).  
It supports **two ways** to integrate with a chatbot or any MCP‑capable host:

1) **HTTP JSON‑RPC (no SDK)** — `http_stats_server.py`  
   Speak **pure JSON‑RPC 2.0** over HTTP. Ideal when you want wire‑level control and to demonstrate MCP without an SDK.

2) **STDIO (SDK‑based)** — `server.py`  
   A classic STDIO MCP server (spawned as a child process by the host). Uses the Python MCP utilities/SDK.

> **Data**: Put the CSV files in `./data/` (or point `STATS_DATA_PATH` to a custom folder).  
> CSV naming must match the dataset filenames exactly (e.g., `Player Per Game.csv`, `Team Summaries.csv`, etc.).

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Mode A — HTTP JSON‑RPC (no SDK)](#mode-a--http-json-rpc-no-sdk)
  - [Start the server](#start-the-server)
  - [JSON‑RPC endpoint and examples](#json-rpc-endpoint-and-examples)
  - [Integrate with your chatbot](#integrate-with-your-chatbot)
- [Mode B — STDIO (SDK)](#mode-b--stdio-sdk)
  - [Diagnostic run](#diagnostic-run)
  - [Integrate with your chatbot](#integrate-with-your-chatbot-1)
- [Tools (capabilities)](#tools-capabilities)
- [CSV data files](#csv-data-files)
- [Troubleshooting](#troubleshooting)
- [License & data credit](#license--data-credit)

---

## Features

- **Local, offline analytics** over NBA CSVs; no external API calls.
- **Two integration modes**: HTTP JSON‑RPC (no SDK) and STDIO (SDK).
- **Fast CSV engine** with `pandas`, lazy‑loaded and cached on first use.
- **Fuzzy player/team matching** (accepts minor typos and team abbreviations like `CHI`, `LAL`).
- **Deterministic output**: each tool returns a single text block with a **human‑readable summary** (can also be parsed as needed).
- **Host‑agnostic**: works with DunkMaster or any MCP‑capable client.

---

## Requirements

- Python **3.10+**
- `pip install -r requirements.txt`
- CSVs present under `./data/` (or set `STATS_DATA_PATH`)

---

## Mode A — HTTP JSON‑RPC (no SDK)

### Start the server

**Windows (PowerShell):**
```powershell
# In this repo (MCP-Local-DunkMaster)
$env:STATS_DATA_PATH = "C:/full/path/to/MCP-Local-DunkMaster/data"
python http_stats_server.py
# → Uvicorn running on http://0.0.0.0:9000
```
**macOS/Linux (bash):**
```bash
export STATS_DATA_PATH="$HOME/path/to/MCP-Local-DunkMaster/data"
python http_stats_server.py
# → running on http://0.0.0.0:9000
```

### JSON‑RPC endpoint and examples

- **URL**: `http://127.0.0.1:9000/jsonrpc`
- **Method**: `POST`
- **Content‑Type**: `application/json`
- **Methods implemented**:
  - `initialize` → `{"protocolVersion": "2.0"}`
  - `tools/list` → `{"tools":[ ... ]}`
  - `tools/call` → executes a tool by name with arguments
  - `shutdown`

**PowerShell examples:**
```powershell
$URL = "http://127.0.0.1:9000/jsonrpc"

# 1) Initialize
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' $URL

# 2) List tools
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' $URL

# 3) Call a tool: player_summary
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"player_summary","arguments":{"player":"Michael Jordan"}}}' $URL

# 4) Call a tool: team_summary (by name or abbreviation)
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_summary","arguments":{"season":1996,"team":"Chicago Bulls"}}}' $URL
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"team_summary","arguments":{"season":1996,"team":"CHI"}}}' $URL
```

**cURL equivalents:**
```bash
URL=http://127.0.0.1:9000/jsonrpc

curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' $URL

curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' $URL

curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"player_summary","arguments":{"player":"Michael Jordan"}}}' $URL

curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_summary","arguments":{"season":1996,"team":"Chicago Bulls"}}}' $URL
```

### Integrate with your chatbot

Set in your **host/chatbot** project:
```
STATS_MCP_URL=http://127.0.0.1:9000/jsonrpc
```
Your host should POST JSON‑RPC requests to that URL and consume responses like:
```json
{"content":[{"type":"text","text":"...human friendly summary..."}], "isError": false}
```
If you’re using **DunkMaster**, it auto‑detects `STATS_MCP_URL` and will route `stats.*` steps through HTTP JSON‑RPC.

---

## Mode B — STDIO (SDK)

### Diagnostic run

You normally **don’t** run the STDIO server directly—your host will spawn it. To verify it boots with your CSVs:

```bash
python server.py --data ./data
# The process waits for STDIO JSON-RPC; Ctrl+C to stop
```

### Integrate with your chatbot

In the **host/chatbot** project set:
```
STATS_MCP_PATH=C:/full/path/to/MCP-Local-DunkMaster/server.py
STATS_DATA_PATH=C:/full/path/to/MCP-Local-DunkMaster/data
```
The host should spawn:
```
python <STATS_MCP_PATH> --data <STATS_DATA_PATH>
```
…and then talk MCP via **STDIO** (initialize → list_tools → call_tool).  
On Windows: avoid quotes in env values; use forward slashes for long paths with spaces.

---

## Tools (capabilities)

> All tools return a single “text” content block (human‑readable). Your host can display it directly or parse metrics if needed.

- **`player_summary`**  
  **Args**: `{"player": "Michael Jordan"}`  
  **Uses**: `Player Per Game.csv` (+ optionally `Player Totals.csv`, `All‑Star Selections.csv`, `Player Award Shares.csv`, `Player Career Info.csv`).  
  **Output**: seasons span, teams, rough career averages (PPG/RPG/APG), awards/All‑Stars summary.

- **`top_scorers`**  
  **Args**: `{"season": 1996, "n": 10}`  
  **Uses**: `Player Per Game.csv`.  
  **Output**: Top‑N by `pts_per_game` for the season.

- **`compare_players`**  
  **Args**: `{"player_a": "...", "player_b": "...", "basis": "per_game|per_36|per_100"}`  
  **Uses**: `Player Per Game.csv`, `Per 36 Minutes.csv`, `Per 100 Poss.csv`.  
  **Output**: Side‑by‑side weighted career averages for the basis.

- **`team_summary`**  
  **Args**: `{"season": 1996, "team": "Chicago Bulls"}` (or `"CHI"`)  
  **Uses**: `Team Summaries.csv` + `Team Stats Per Game.csv`.  
  **Output**: W‑L, SRS, ORtg, DRtg, Net, Pace, TS%, eFG%, TOV%, ORB%, FT/FGA, PTS/G, TRB/G, AST/G, 3P%.  
  **Matching**: name or abbreviation; prefers regular‑season rows.

---

## CSV data files

Place the files under `./data/` (or point `STATS_DATA_PATH`). Filenames must match **exactly** (case‑sensitive on macOS/Linux).  
Full set (22 files):

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

---

## Troubleshooting

- **`FileNotFoundError: Missing CSV`**  
  Ensure exact filenames in `./data/`. On macOS/Linux the filesystem is case‑sensitive.

- **HTTP port already in use** (Mode A)  
  Use another port: `PORT=9010 python http_stats_server.py` → call `http://127.0.0.1:9010/jsonrpc`.

- **STDIO server exits immediately** (Mode B)  
  - Spawn it with the **same interpreter** as the host (`sys.executable`).
  - Install deps in that venv: `pip install -r requirements.txt`.
  - Avoid quotes in `STATS_MCP_PATH`/`STATS_DATA_PATH`. Prefer forward slashes in long paths.

- **Unexpected fuzzy matches**  
  Try the exact name or team abbreviation; add disambiguation logic in your host if needed.

---

## License & data credit

- **Code**: MIT (see `LICENSE`).
- **Data**: consolidated public basketball datasets; classroom reference: <https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats>.

Happy hacking! 🏀
