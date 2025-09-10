
"""
Local NBA Stats MCP (fastmcp)

Exposes JSON-RPC tools over STDIO so your chatbot can query NBA CSV datasets.
Tools:
  - player_summary(player): compact career overview + awards/all-star
  - top_scorers(season, n): top-N PPG for a season
  - compare_players(a, b, basis): compare career avgs (per_game | per_36 | per_100)
  - team_summary(season, team): SRS/ORtg/DRtg/pace/W-L from Team Summaries

Run:
  python server.py --data <folder-with-22-csvs>
Your host (chatbot) should spawn this process via STDIO or use your HTTP bridge.
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from rapidfuzz import process, fuzz
from mcp.server.fastmcp import FastMCP

# Loaded once in main()
TABLES = None

@dataclass
class Tables:
    per_game: pd.DataFrame
    per36: pd.DataFrame
    per100: pd.DataFrame
    totals: pd.DataFrame
    career: pd.DataFrame
    allstar: pd.DataFrame
    awards: pd.DataFrame
    team_summ: pd.DataFrame


def load_tables(data_dir: Path) -> Tables:
    """Read required CSVs and normalize common columns."""
    def rd(name: str) -> pd.DataFrame:
        p = data_dir / name
        if not p.exists():
            raise FileNotFoundError(f"Missing CSV: {p}")
        return pd.read_csv(p, encoding="utf-8")

    per_game = rd("Player Per Game.csv")
    per36 = rd("Per 36 Minutes.csv")
    per100 = rd("Per 100 Poss.csv")
    totals = rd("Player Totals.csv")
    career = rd("Player Career Info.csv")
    allstar = rd("All-Star Selections.csv")
    awards = rd("Player Award Shares.csv")
    team_summ = rd("Team Summaries.csv")

    # Season as numeric
    for df in (per_game, per36, per100, totals, team_summ):
        if "season" in df.columns:
            df["season"] = pd.to_numeric(df["season"], errors="coerce")

    # Trim player names
    for df in (per_game, per36, per100, totals, career, allstar, awards):
        if "player" in df.columns:
            df["player"] = df["player"].astype(str).str.strip()

    return Tables(per_game, per36, per100, totals, career, allstar, awards, team_summ)


# Utils

def _best_match(name: str, choices: List[str]) -> Tuple[str, float]:
    """Fuzzy-match a name against a list of choices."""
    if not choices:
        return name, 0.0
    match, score, _ = process.extractOne(name, choices, scorer=fuzz.WRatio)
    return match, float(score or 0.0)


def _ensure_loaded():
    """Guard: tools require tables loaded in main()."""
    if TABLES is None:
        raise RuntimeError(
            "Server not initialized. Run: python server.py --data <folder-with-csvs>"
        )


def _json(obj: Any) -> str:
    """Pretty JSON for text content blocks."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


# FastMCP server instance
mcp = FastMCP("DunkMaster Stats MCP (Local)")


@mcp.tool(name="player_summary")
def player_summary(player: str) -> str:
    """Compact career summary with span, teams, weighted career averages, all-star & top award shares."""
    _ensure_loaded()
    T = TABLES

    choices = sorted(set(T.per_game["player"].dropna().astype(str)))
    best, score = _best_match(player, choices)

    pdf = T.per_game[T.per_game["player"] == best].copy()
    tdf = T.totals[T.totals["player"] == best].copy()
    cdf = T.career[T.career["player"] == best].copy()
    adf = T.allstar[T.allstar["player"] == best].copy()
    wdf = T.awards[T.awards["player"] == best].copy()

    if pdf.empty and tdf.empty and cdf.empty:
        return _json(
            {"match": None, "score": 0.0, "error": f"Player '{player}' not found."}
        )

    seasons = sorted(pdf["season"].dropna().unique().tolist()) if "season" in pdf else []
    span = (min(seasons), max(seasons)) if seasons else (None, None)
    teams = sorted(set(pdf["team"].dropna().astype(str))) if "team" in pdf.columns else []

    def wavg(df: pd.DataFrame, num: str, den: str = "g") -> Optional[float]:
        """Game-weighted average: sum(num * g) / sum(g)."""
        if num not in df.columns or den not in df.columns:
            return None
        sub = df[[num, den]].dropna()
        if sub.empty:
            return None
        return float((sub[num] * sub[den]).sum() / sub[den].sum())

    pts = wavg(pdf, "pts_per_game") or wavg(tdf, "pts")
    ast = wavg(pdf, "ast_per_game") or wavg(tdf, "ast")
    trb = wavg(pdf, "trb_per_game") or wavg(tdf, "trb")

    allstar_count = int(adf.shape[0]) if not adf.empty else 0
    top_awards = []
    if not wdf.empty and "award" in wdf.columns:
        top_awards = (
            wdf.groupby("award")
            .apply(lambda g: g.sort_values("share", ascending=False).head(1))
            .reset_index(drop=True)[["award", "season", "share", "winner"]]
            .to_dict(orient="records")
        )

    return _json(
        {
            "match": best,
            "score": score,
            "span": {"from": span[0], "to": span[1]},
            "teams": teams,
            "career_avgs": {
                "pts": round(pts, 2) if pts is not None else None,
                "ast": round(ast, 2) if ast is not None else None,
                "trb": round(trb, 2) if trb is not None else None,
            },
            "all_star_selections": allstar_count,
            "top_award_shares": top_awards,
        }
    )


@mcp.tool(name="top_scorers")
def top_scorers(season: int, n: int = 10) -> str:
    """Return top-N by points per game for a season."""
    _ensure_loaded()
    T = TABLES
    df = T.per_game[T.per_game["season"] == season].copy()
    if df.empty or "pts_per_game" not in df.columns:
        return _json([])
    out = (
        df[["player", "team", "pts_per_game", "g"]]
        .dropna()
        .sort_values("pts_per_game", ascending=False)
        .head(int(n))
    )
    return _json(out.to_dict(orient="records"))


@mcp.tool(name="compare_players")
def compare_players(player_a: str, player_b: str, basis: str = "per_game") -> str:
    """Compare career averages using a basis: per_game | per_36 | per_100."""
    _ensure_loaded()
    T = TABLES
    basis_map = {
        "per_game": (
            T.per_game,
            {"pts": "pts_per_game", "ast": "ast_per_game", "trb": "trb_per_game"},
        ),
        "per_36": (
            T.per36,
            {"pts": "pts_per_36_min", "ast": "ast_per_36_min", "trb": "trb_per_36_min"},
        ),
        "per_100": (
            T.per100,
            {
                "pts": "pts_per_100_poss",
                "ast": "ast_per_100_poss",
                "trb": "trb_per_100_poss",
            },
        ),
    }
    if basis not in basis_map:
        basis = "per_game"
    df, cols = basis_map[basis]

    choices = sorted(set(df["player"].dropna().astype(str)))
    a_name, a_score = _best_match(player_a, choices)
    b_name, b_score = _best_match(player_b, choices)

    def career(subdf: pd.DataFrame, who: str) -> Dict[str, Any]:
        sub = subdf[subdf["player"] == who]
        if sub.empty:
            return {"match": who, "g": 0, "pts": None, "ast": None, "trb": None}
        g = sub["g"].dropna()
        gsum = float(g.sum()) if not g.empty else 0.0

        def wavg(col: str) -> Optional[float]:
            if col not in sub.columns or gsum == 0:
                return None
            return float((sub[col] * sub["g"]).sum() / gsum)

        return {
            "match": who,
            "g": int(gsum),
            "pts": round(wavg(cols["pts"]), 2) if wavg(cols["pts"]) is not None else None,
            "ast": round(wavg(cols["ast"]), 2) if wavg(cols["ast"]) is not None else None,
            "trb": round(wavg(cols["trb"]), 2) if wavg(cols["trb"]) is not None else None,
        }

    result = {
        "basis": basis,
        "player_a": career(df, a_name) | {"score": a_score},
        "player_b": career(df, b_name) | {"score": b_score},
    }
    return _json(result)


@mcp.tool(name="team_summary")
def team_summary(season: int, team: str) -> str:
    """Return W/L, SRS, ORtg, DRtg, pace, and a few shooting/possession metrics."""
    _ensure_loaded()
    T = TABLES
    df = T.team_summ[T.team_summ["season"] == season].copy()
    if df.empty:
        return _json({"error": f"No data for season {season}"})
    choices = sorted(set(df["team"].dropna().astype(str)))
    best, score = _best_match(team, choices)
    row = df[df["team"] == best].head(1)
    if row.empty:
        return _json({"match": None, "score": 0.0, "error": f"Team '{team}' not found"})
    r = row.iloc[0].to_dict()
    fields = [
        "w", "l", "srs", "o_rtg", "d_rtg", "n_rtg", "pace",
        "ts_percent", "e_fg_percent", "tov_percent", "orb_percent",
    ]
    return _json(
        {
            "match": best,
            "score": score,
            "season": int(season),
            "summary": {k: r.get(k) for k in fields if k in r},
        }
    )


# Main entry point

def main():
    """Parse args, load CSVs, and start the FastMCP STDIO loop."""
    global TABLES
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to folder containing the 22 CSV files.")
    args = parser.parse_args()

    data_dir = Path(args.data).expanduser().resolve()
    if not data_dir.exists():
        raise SystemExit(f"Data folder does not exist: {data_dir}")

    TABLES = load_tables(data_dir)

    # Start STDIO server (host speaks JSON-RPC over stdin/stdout).
    if hasattr(mcp, "run_stdio"):
        mcp.run_stdio()
    elif hasattr(mcp, "run"):
        mcp.run()
    else:
        raise RuntimeError("This fastmcp version exposes neither run_stdio() nor run(). Please upgrade 'mcp'.")


if __name__ == "__main__":
    main()
