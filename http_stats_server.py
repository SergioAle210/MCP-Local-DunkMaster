from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import pandas as pd
from pathlib import Path
import os
import uvicorn

"""
HTTP JSON-RPC bridge for local NBA CSV analytics.

This service exposes a minimal JSON-RPC 2.0 API over HTTP so hosts WITHOUT an MCP SDK
can call the same tools your STDIO MCP provides:

Methods:
  - initialize -> {"protocolVersion": "2.0"}
  - tools/list -> {"tools": [...]}
  - tools/call -> {"content":[{"type":"text","text":"..."}], "isError": false}
  - shutdown   -> {"ok": true}

Tools:
  - player_summary(player)
  - top_scorers(season, n=10)
  - compare_players(player_a, player_b, basis="per_game")
  - team_summary(season, team)

Run:
  STATS_DATA_PATH=/path/to/csvs python http_stats_server.py
"""

app = FastAPI()

# Folder with the 22 CSVs (defaults to ./data for local tests)
DATA_DIR = Path(os.getenv("STATS_DATA_PATH", "./data")).resolve()

# Lazy-loaded dataframes (load on first use)
players_per_game = None
players_totals = None
team_summaries = None
team_stats_pg = None


def _ensure_loaded():
    """Ensure player-level CSVs are loaded in memory."""
    global players_per_game, players_totals
    if players_per_game is None:
        p = DATA_DIR / "Player Per Game.csv"
        if not p.exists():
            raise FileNotFoundError(f"Missing CSV: {p}")
        players_per_game = pd.read_csv(p)
    if players_totals is None:
        p = DATA_DIR / "Player Totals.csv"
        if not p.exists():
            raise FileNotFoundError(f"Missing CSV: {p}")
        players_totals = pd.read_csv(p)


def _load_csv(name: str, **kwargs):
    """Read an arbitrary CSV from DATA_DIR with basic existence check."""
    p = DATA_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Missing CSV: {p}")
    return pd.read_csv(p, **kwargs)


def _ensure_loaded_teams():
    """Lazy-load team-level CSVs needed by team_summary()."""
    global team_summaries, team_stats_pg
    if team_summaries is None:
        # Contains: w,l,srs,o_rtg,d_rtg,n_rtg,pace,ts_percent,e_fg_percent,tov_percent,orb_percent,ft_fga,abbreviation,playoffs,...
        team_summaries = _load_csv("Team Summaries.csv")
    if team_stats_pg is None:
        # Per-game team stats: pts_per_game, ast_per_game, trb_per_game, x3p_percent, ...
        team_stats_pg = _load_csv("Team Stats Per Game.csv")


def _match_team_row(df: pd.DataFrame, season: int, team: str):
    """
    Return a single row for (season, team) by name or abbreviation.
    Prefer regular season rows when `playoffs` column exists.
    """
    sub = df[df["season"] == season]
    if sub.empty:
        return None
    t = str(team).strip().lower()

    def _by_name_or_abbr(frame):
        m = frame[frame["team"].str.lower() == t] if "team" in frame.columns else pd.DataFrame()
        if m.empty and "abbreviation" in frame.columns:
            m = frame[frame["abbreviation"].str.lower() == t]
        if m.empty and "team" in frame.columns:
            # substring fallback
            m = frame[frame["team"].str.lower().str.contains(t, na=False)]
        return m

    m = _by_name_or_abbr(sub)
    if m.empty:
        return None
    if "playoffs" in m.columns:
        reg = m[m["playoffs"] == 0]
        if not reg.empty:
            m = reg
    return m.iloc[0]

def _pct(x):
    try:
        v = float(x)
        if pd.isna(v):
            return float("nan")
        return v*100.0 if v <= 1.0 else v
    except Exception:
        return float("nan")

# Tool implementations (return plain text)
def tool_player_summary(player: str) -> str:
    """Compact career line based on Player Per Game (mean across seasons)."""
    _ensure_loaded()
    df = players_per_game
    sub = df[df["player"].str.lower() == player.lower()]
    if sub.empty:
        return f"No stats for {player}."
    seasons = sub["season"].nunique()
    ppg = sub["pts_per_game"].mean()
    apg = sub["ast_per_game"].mean()
    rpg = sub["trb_per_game"].mean() if "trb_per_game" in sub.columns else (sub["orb_per_game"] + sub["drb_per_game"]).mean()
    return f"{player}: {seasons} seasons. Career averages ~ {ppg:.1f} PPG, {rpg:.1f} RPG, {apg:.1f} APG."


def tool_top_scorers(season: int, n: int = 10) -> str:
    """Top-N by points per game for a given season."""
    _ensure_loaded()
    df = players_per_game
    sub = df[df["season"] == season].copy()
    if sub.empty:
        return f"No season data for {season}."
    top = sub.sort_values("pts_per_game", ascending=False).head(int(n))
    lines = [f"{i+1}. {row['player']} — {row['pts_per_game']:.1f} PPG" for i, row in top.reset_index(drop=True).iterrows()]
    return f"Top scorers {season}:\n" + "\n".join(lines)


def tool_compare_players(player_a: str, player_b: str, basis: str = "per_game") -> str:
    """Basic comparison using Player Per Game columns; returns a single-line summary."""
    _ensure_loaded()
    df = players_per_game
    A = df[df["player"].str.lower() == player_a.lower()]
    B = df[df["player"].str.lower() == player_b.lower()]
    if A.empty or B.empty:
        return "Not enough data for comparison."

    def line(name, d):
        rpg_series = d["trb_per_game"] if "trb_per_game" in d.columns else (d["orb_per_game"] + d["drb_per_game"])
        return f"{name}: PPG {d['pts_per_game'].mean():.1f}, APG {d['ast_per_game'].mean():.1f}, RPG {rpg_series.mean():.1f}"

    return line(player_a, A) + " | " + line(player_b, B)


def tool_team_summary(season: int, team: str) -> str:
    """Mix advanced metrics (Team Summaries) with per-game stats (Team Stats Per Game)."""
    _ensure_loaded_teams()
    row_sum = _match_team_row(team_summaries, season, team)
    if row_sum is None:
        return f"No team summary for {team} in {season}."

    # Advanced metrics
    abbr = row_sum.get("abbreviation", "")
    w = int(row_sum.get("w", 0))
    l = int(row_sum.get("l", 0))
    srs  = float(row_sum.get("srs", float("nan")))
    ortg = float(row_sum.get("o_rtg", float("nan")))
    drtg = float(row_sum.get("d_rtg", float("nan")))
    nrtg = float(row_sum.get("n_rtg", (ortg - drtg) if (pd.notna(ortg) and pd.notna(drtg)) else float("nan")))
    pace = float(row_sum.get("pace", float("nan")))
    ts   = _pct(row_sum.get("ts_percent"))
    efg  = _pct(row_sum.get("e_fg_percent"))
    tov  = _pct(row_sum.get("tov_percent"))
    orb  = _pct(row_sum.get("orb_percent"))
    ftfga = float(row_sum.get("ft_fga", float("nan")))

    # Per-game box stats
    row_pg = _match_team_row(team_stats_pg, season, team)
    pts_pg = float(row_pg.get("pts_per_game", float("nan"))) if row_pg is not None else float("nan")
    ast_pg = float(row_pg.get("ast_per_game", float("nan"))) if row_pg is not None else float("nan")
    trb_pg = float(row_pg.get("trb_per_game", float("nan"))) if row_pg is not None else float("nan")
    x3p_pct = _pct(row_pg.get("x3p_percent")) if row_pg is not None else float("nan")

    name_out = row_sum.get("team", team)
    abbr_out = f" ({abbr})" if abbr else ""
    parts = [
        f"{name_out}{abbr_out} {season} RS: {w}-{l}",
        f"SRS {srs:.1f}" if pd.notna(srs) else None,
        f"ORtg {ortg:.1f}" if pd.notna(ortg) else None,
        f"DRtg {drtg:.1f}" if pd.notna(drtg) else None,
        f"Net {nrtg:+.1f}" if pd.notna(nrtg) else None,
        f"Pace {pace:.1f}" if pd.notna(pace) else None,
        f"TS% {ts:.1f}" if pd.notna(ts) else None,
        f"eFG% {efg:.1f}" if pd.notna(efg) else None,
        f"TOV% {tov:.1f}" if pd.notna(tov) else None,
        f"ORB% {orb:.1f}" if pd.notna(orb) else None,
        f"FT/FGA {ftfga:.3f}" if pd.notna(ftfga) else None,
        f"PTS/G {pts_pg:.1f}" if pd.notna(pts_pg) else None,
        f"TRB/G {trb_pg:.1f}" if pd.notna(trb_pg) else None,
        f"AST/G {ast_pg:.1f}" if pd.notna(ast_pg) else None,
        f"3P% {x3p_pct:.1f}" if pd.notna(x3p_pct) else None,
    ]
    text = ", ".join([p for p in parts if p])
    return text or f"{name_out} {season}: no metrics found."


# Tools descriptor (mirrors MCP list_tools shape loosely)
TOOLS = [
    {"name": "player_summary",   "description": "Summary for a player", "inputSchema": {"type": "object", "properties": {"player": {"type": "string"}}, "required": ["player"]}},
    {"name": "top_scorers",      "description": "Top scorers in a season", "inputSchema": {"type": "object", "properties": {"season": {"type":"integer"}, "n":{"type":"integer"}}, "required": ["season"]}},
    {"name": "compare_players",  "description": "Compare two players", "inputSchema": {"type": "object", "properties": {"player_a":{"type":"string"}, "player_b":{"type":"string"}, "basis":{"type":"string"}}, "required": ["player_a","player_b"]}},
    {"name": "team_summary",     "description": "Team summary in a season", "inputSchema": {"type": "object", "properties": {"season":{"type":"integer"}, "team":{"type":"string"}}, "required": ["season","team"]}},
]


def _jsonrpc_result(id_, result):
    """Helper: JSON-RPC success envelope."""
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _jsonrpc_error(id_, code, message):
    """Helper: JSON-RPC error envelope."""
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


@app.post("/jsonrpc")
async def jsonrpc(request: Request):
    """
    Minimal JSON-RPC 2.0 endpoint compatible with a bare HTTP client.
    Expects: {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{...}}
    """
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {}) or {}
    id_ = body.get("id")

    try:
        if method == "initialize":
            return JSONResponse(_jsonrpc_result(id_, {"protocolVersion": "2.0"}))

        if method == "tools/list":
            return JSONResponse(_jsonrpc_result(id_, {"tools": TOOLS}))

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {}) or {}
            if name == "player_summary":
                text = tool_player_summary(args.get("player", ""))
            elif name == "top_scorers":
                text = tool_top_scorers(int(args.get("season", 0)), int(args.get("n", 10)))
            elif name == "compare_players":
                text = tool_compare_players(args.get("player_a", ""), args.get("player_b", ""), args.get("basis", "per_game"))
            elif name == "team_summary":
                text = tool_team_summary(int(args.get("season", 0)), args.get("team", ""))
            else:
                return JSONResponse(_jsonrpc_error(id_, -32601, f"Unknown tool: {name}"))
            # mimic MCP content blocks
            return JSONResponse(_jsonrpc_result(id_, {"content": [{"type": "text", "text": text}], "isError": False}))

        if method == "shutdown":
            return JSONResponse(_jsonrpc_result(id_, {"ok": True}))

        return JSONResponse(_jsonrpc_error(id_, -32601, "Method not found"))
    except Exception as e:
        return JSONResponse(_jsonrpc_error(id_, -32000, str(e)))


if __name__ == "__main__":
    # For local development. Cloud providers typically inject $PORT.
    port = int(os.getenv("PORT", "9000"))
    uvicorn.run("http_stats_server:app", host="0.0.0.0", port=port)
