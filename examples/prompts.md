# Prompts — MCP‑Local‑DunkMaster (NBA Stats)

These prompts are designed for your **chatbot** that integrates the local NBA statistics MCP.  
They work with **both integration modes**: **HTTP JSON‑RPC** (`STATS_MCP_URL`) and **STDIO** (`STATS_MCP_PATH` + `STATS_DATA_PATH`).

> Tip: after each action, have your host print the tool output and/or show a tail of `logs/mcp.jsonl` to evidence `initialize`, `tools/list`, and `tools/call` traffic.

---

## Player summaries

1. “Give me the **summary for Michael Jordan** using the stats server.”  
2. “What is the **career span** and which **teams** did **Kobe Bryant** play for?”  
3. “Career averages (PTS/AST/TRB) for **Tim Duncan**.”  
4. “How many **All‑Star selections** does **LeBron James** have?”

## Top scorers by season

5. “Top **10 scorers** for **1996**.”  
6. “Top **5 scorers** for **2016**.”  
7. “Top **15 scorers** for **1988**.”

## Compare players

8. “Compare **Michael Jordan** vs **LeBron James** by **per_game**.”  
9. “Compare **Stephen Curry** vs **Damian Lillard** by **per_36**.”  
10. “Compare **Larry Bird** vs **Magic Johnson** by **per_100**.”

## Team summaries

11. “Give me the **Chicago Bulls 1996 summary** (SRS, ORtg, DRtg, Pace, W‑L).”  
12. “Summary of **Miami Heat 2013**.”  
13. “Summary of **San Antonio Spurs 2007**.”  
14. “Summary of **CHI 1996** (abbreviation).”

---

## Bonus (mixing FS/Git + Stats via your host)

15. “Append the **Michael Jordan summary** to `report.md` and **commit** with message `docs: add MJ summary`.”  
16. “Compare **Jordan** vs **LeBron** by **per_36** and **save** the result to `comparisons/mj_lb.json`.”

> (15–16 require your host to also integrate **Filesystem MCP** and **Git MCP**.)

---

## Expected output

- The server returns a **single text block** (human‑readable, JSON‑like).  
- Player and team names support **fuzzy matching** (minor typos, abbreviations like `CHI`, `LAL`). If results look odd, try the exact name.  
- Season must be an **integer** (e.g., `1996`).

---

## Manual tests (no chatbot) — HTTP JSON‑RPC

**PowerShell**

```powershell
$URL = "http://127.0.0.1:9000/jsonrpc"

# initialize
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' $URL

# list tools
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' $URL

# player summary
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"player_summary","arguments":{"player":"Michael Jordan"}}}' $URL

# team summary (name and abbreviation)
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_summary","arguments":{"season":1996,"team":"Chicago Bulls"}}}' $URL
irm -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"team_summary","arguments":{"season":1996,"team":"CHI"}}}' $URL
```

**cURL**

```bash
URL=http://127.0.0.1:9000/jsonrpc

curl -s -X POST -H "Content-Type: application/json"   -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' $URL

curl -s -X POST -H "Content-Type: application/json"   -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' $URL

curl -s -X POST -H "Content-Type: application/json"   -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"player_summary","arguments":{"player":"Michael Jordan"}}}' $URL

curl -s -X POST -H "Content-Type: application/json"   -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_summary","arguments":{"season":1996,"team":"Chicago Bulls"}}}' $URL
```

---

## Screenshot suggestions

1. **HTTP JSON‑RPC — server running**  
   Console with `python http_stats_server.py` and the line:  
   *“Uvicorn running on http://0.0.0.0:9000”*.

2. **HTTP JSON‑RPC — tools/list**  
   PowerShell/cURL output showing `player_summary`, `top_scorers`, `compare_players`, `team_summary`.

3. **Host integration (HTTP)**  
   Your chatbot running: “Give me the Chicago Bulls 1996 summary” and showing the returned text.

4. **STDIO — host env**  
   Screenshot of the host `.env` with `STATS_MCP_PATH` and `STATS_DATA_PATH` configured.

5. **Host integration (STDIO)**  
   Chatbot running: “Top 5 scorers of 1996” with the result (and, if available, a sidebar with executed steps).

6. **Logging evidence**  
   Tail of `logs/mcp.jsonl` showing `sync/request/response` for `initialize`, `tools/list`, `tools/call`.
