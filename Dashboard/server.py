from __future__ import annotations

import copy
import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "Dashboard"
sys.path.insert(0, str(ROOT))

from Code.rr_auction_simulator import (
    add_player_valuation_columns,
    build_team_states,
    english_auction_price,
    load_auction_pool,
    randomize_within_set_order,
    resolve_team_configs,
    run_auction_with_team_configs,
    team_player_valuation,
)


def ensure_dashboard_data() -> None:
    data_path = DASHBOARD_DIR / "data" / "dashboard_data.js"
    if data_path.exists():
        return
    from Dashboard.build_dashboard_data import main as build_dashboard_data_main

    build_dashboard_data_main()


def load_dashboard_payload() -> dict:
    ensure_dashboard_data()
    data_path = DASHBOARD_DIR / "data" / "dashboard_data.js"
    raw = data_path.read_text(encoding="utf-8")
    prefix = "window.DASHBOARD_DATA = "
    if not raw.startswith(prefix):
        raise ValueError("Unexpected dashboard data format")
    return json.loads(raw[len(prefix):].rstrip(";\n "))


def parse_retained_players(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def apply_team_override(team_config: dict, override: dict) -> dict:
    updated = copy.deepcopy(team_config)
    if "purse" in override:
        updated["purse"] = float(override["purse"])
    if "retained" in override:
        updated["retained"] = int(override["retained"])
    if "overseas_retained" in override:
        updated["overseas_retained"] = int(override["overseas_retained"])
    retained_players = parse_retained_players(override.get("retained_players"))
    if retained_players:
        updated["retained_players"] = retained_players
    if isinstance(override.get("role_needs"), dict):
        updated["role_needs"] = {str(k): float(v) for k, v in override["role_needs"].items()}
        # Scenario edits should override canned franchise playbooks.
        updated["focus_strategy"] = {}
        updated["role_caps"] = {
            role: round(float(updated["purse"]) * min(0.55, 0.08 + 0.18 * max(0.0, weight)), 2)
            for role, weight in updated["role_needs"].items()
            if float(weight) > 0
        }
    return updated


def build_scenario_response(payload: dict) -> dict:
    focus_team = str(payload.get("team") or "RR").upper()
    season = str(payload.get("season") or "2026")
    team_configs = resolve_team_configs(season=season)
    if focus_team not in team_configs:
        raise ValueError(f"Unknown team code: {focus_team}")

    if any(key in payload for key in ("purse", "retained", "overseas_retained", "retained_players", "role_needs")):
        team_configs[focus_team] = apply_team_override(team_configs[focus_team], payload)

    team_overrides = payload.get("team_overrides", {})
    if isinstance(team_overrides, dict):
        for team_code, override in team_overrides.items():
            code = str(team_code).upper()
            if code in team_configs and isinstance(override, dict):
                team_configs[code] = apply_team_override(team_configs[code], override)

    debug_player = str(payload.get("debug_player") or "").strip()

    events_df, focus_df, teams = run_auction_with_team_configs(
        team_configs=team_configs,
        focus_team=focus_team,
        season=season,
        randomize_within_set=True,
        seed=int(payload.get("seed", 0)),
    )

    focus_state = teams[focus_team]
    high_need_roles = {
        role for role, weight in focus_state.role_needs.items() if float(weight) >= 0.5
    }
    missed_df = events_df[
        events_df["winner"].notna()
        & (events_df["winner"] != focus_team)
        & (events_df["role_bucket"].isin(high_need_roles))
    ].copy()
    missed_df = missed_df.sort_values(["set_no", "final_price"], ascending=[True, False]).head(12)

    rival_pressure = [
        {
            "team_code": code,
            "purse_left": round(float(state.purse), 2),
            "purchases": len(state.purchases),
        }
        for code, state in teams.items()
        if code != focus_team
    ]
    rival_pressure.sort(key=lambda row: row["purse_left"], reverse=True)

    debug = build_bid_ladder_debug(
        team_configs=team_configs,
        focus_team=focus_team,
        season=season,
        seed=int(payload.get("seed", 0)),
        debug_player=debug_player,
    )

    return {
        "team": focus_team,
        "season": season,
        "focus_buys": focus_df[
            ["set_no", "player_name", "role_bucket", "final_price", "runner_up", "quality_score"]
        ].to_dict("records"),
        "missed_targets": missed_df[
            ["set_no", "player_name", "role_bucket", "winner", "final_price", "runner_up", "quality_score"]
        ].to_dict("records"),
        "summary": {
            "purse_left": round(float(focus_state.purse), 2),
            "overseas_slots_left": int(focus_state.overseas_slots_left),
            "players_won": int(len(focus_state.purchases)),
            "high_need_roles": sorted(high_need_roles),
        },
        "rival_pressure": rival_pressure[:5],
        "debug": debug,
    }


def build_match_brief_response(payload: dict) -> dict:
    match_id = int(payload.get("match_id") or 0)
    team_lens = str(payload.get("team_lens") or "").upper()
    model = str(payload.get("model") or os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured on the server")

    dashboard_payload = load_dashboard_payload()
    planning = dashboard_payload.get("match_planning", {})
    matches = planning.get("matches", [])
    match = next((row for row in matches if int(row.get("match_id", 0)) == match_id), None)
    if not match:
        raise ValueError(f"Unknown match_id: {match_id}")

    if team_lens not in {match["home"], match["away"]}:
        team_lens = match["home"]

    focus = match["home_analysis"] if team_lens == match["home"] else match["away_analysis"]
    opposition = match["away_analysis"] if team_lens == match["home"] else match["home_analysis"]
    opposition_code = match["away"] if team_lens == match["home"] else match["home"]

    context = {
        "match": {
            "label": match["label"],
            "date": match["date"],
            "start": match["start"],
            "venue": match["venue"],
            "team_lens": team_lens,
            "opposition": opposition_code,
        },
        "venue_profile": match["venue_profile"],
        "focus_team": focus,
        "opposition_team": opposition,
        "methodology": planning.get("methodology", {}),
    }

    system_prompt = (
        "You are a high-level IPL strategy analyst writing a match brief for a front-office decision-support dashboard. "
        "Use only the provided structured data. Do not invent statistics, players, venue traits, or matchup claims not present in the context. "
        "Be specific, tactical, and cricket-literate. Prefer realistic role language such as opener, enforcer, anchor, death hitter, new-ball bowler, and middle-overs controller. "
        "Return ONLY valid JSON with exactly these keys: headline, opening_call, why_this_matchup_is_live, tactical_edges, matchup_watch, venue_read, risk_flags, recommended_plan. "
        "Each of tactical_edges, matchup_watch, risk_flags, recommended_plan must be an array of 2 to 4 concise strings. "
        "No markdown, no explanation outside the JSON object."
    )

    user_content = (
        "Write a fixture-specific match brief for the selected team lens using this context:\n"
        + json.dumps(context, ensure_ascii=True)
    )

    body = {
        "model": model,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }

    request = Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload_raw = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Claude API error: {exc.code} {detail}") from exc
    except URLError as exc:
        raise ValueError(f"Unable to reach Claude API: {exc.reason}") from exc

    content = payload_raw["content"][0]["text"].strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    try:
        brief = json.loads(content)
    except json.JSONDecodeError:
        brief = {
            "headline": f"{team_lens} Match Brief",
            "opening_call": content,
            "why_this_matchup_is_live": "",
            "tactical_edges": [],
            "matchup_watch": [],
            "venue_read": "",
            "risk_flags": [],
            "recommended_plan": [],
        }

    return {
        "match_id": match_id,
        "team_lens": team_lens,
        "model": model,
        "brief": brief,
    }


def build_bid_ladder_debug(
    team_configs: dict[str, dict],
    focus_team: str,
    season: str,
    seed: int,
    debug_player: str,
) -> dict | None:
    if not debug_player:
        return None

    auction_pool = add_player_valuation_columns(load_auction_pool(season=season), season=season)
    auction_pool = randomize_within_set_order(auction_pool, seed=seed)
    teams = build_team_states(team_configs)

    for idx, player in auction_pool.iterrows():
        valuations: dict[str, float] = {}
        for code, team in teams.items():
            value = team_player_valuation(team, player, idx, auction_pool)
            if value >= player["reserve_price"]:
                valuations[code] = value

        if player["player_name"].lower() == debug_player.lower():
            ordered = sorted(valuations.items(), key=lambda item: (item[1], teams[item[0]].purse), reverse=True)
            clearing_price = (
                round(
                    min(
                        english_auction_price([value for _, value in ordered], float(player["reserve_price"])),
                        ordered[0][1],
                    ),
                    2,
                )
                if ordered
                else None
            )
            winner = ordered[0][0] if ordered else None
            return {
                "player_name": player["player_name"],
                "set_no": int(player["set_no"]),
                "role_bucket": player["role_bucket"],
                "reserve_price": round(float(player["reserve_price"]), 2),
                "quality_score": round(float(player["quality_score"]), 4),
                "base_ceiling": round(float(player["base_ceiling"]), 2),
                "winner": winner,
                "runner_up": ordered[1][0] if len(ordered) > 1 else None,
                "clearing_price": clearing_price,
                "focus_team": focus_team,
                "focus_team_value": valuations.get(focus_team),
                "active_bidders": [
                    {
                        "team_code": code,
                        "valuation": round(float(value), 2),
                        "purse_before": round(float(teams[code].purse), 2),
                    }
                    for code, value in ordered
                ],
            }

        if not valuations:
            continue

        ordered = sorted(valuations.items(), key=lambda item: (item[1], teams[item[0]].purse), reverse=True)
        winner_code, top_value = ordered[0]
        final_price = english_auction_price([value for _, value in ordered], float(player["reserve_price"]))
        if final_price > top_value:
            final_price = top_value
        winner = teams[winner_code]
        winner.purse = round(winner.purse - final_price, 2)
        winner.purchases.append(
            {
                "player_name": player["player_name"],
                "price": final_price,
                "is_overseas": bool(player["is_overseas"]),
                "role_bucket": player["role_bucket"],
                "set_no": int(player["set_no"]),
            }
        )
        winner.role_counts[player["role_bucket"]] = winner.role_counts.get(player["role_bucket"], 0) + 1

    return {"player_name": debug_player, "not_found": True}


_live_score_cache: dict = {"ts": 0.0, "data": None}
_LIVE_CACHE_TTL = 180  # 3 minutes — fits 100 calls/day free tier across a full match


def fetch_live_score() -> dict:
    global _live_score_cache
    now = time.time()
    if _live_score_cache["data"] is not None and now - _live_score_cache["ts"] < _LIVE_CACHE_TTL:
        return _live_score_cache["data"]

    api_key = os.environ.get("CRICAPI_KEY", "").strip()
    if not api_key:
        return {"live": False, "error": "CRICAPI_KEY not configured"}

    url = f"https://api.cricapi.com/v1/currentMatches?apikey={api_key}&offset=0"
    try:
        with urlopen(Request(url, method="GET"), timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"live": False, "error": str(exc)}

    matches = payload.get("data", [])
    rr_match = next(
        (m for m in matches
         if any("rajasthan" in t.lower() for t in m.get("teams", []))),
        None,
    )

    if not rr_match:
        result: dict = {"live": False}
    else:
        started = rr_match.get("matchStarted", False)
        ended   = rr_match.get("matchEnded", False)
        result = {
            "live":      started and not ended,
            "completed": ended,
            "name":      rr_match.get("name", ""),
            "status":    rr_match.get("status", ""),
            "venue":     rr_match.get("venue", ""),
            "teams":     rr_match.get("teams", []),
            "scores": [
                {
                    "inning":   s.get("inning", ""),
                    "runs":     s.get("r", 0),
                    "wickets":  s.get("w", 0),
                    "overs":    s.get("o", 0),
                }
                for s in rr_match.get("score", [])
            ],
        }

    _live_score_cache = {"ts": now, "data": result}
    return result


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/live-score":
            try:
                response = fetch_live_score()
                body = json.dumps(response).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:  # noqa: BLE001
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/run-scenario", "/api/match-brief", "/api/live-score"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8") or "{}")
            if parsed.path == "/api/run-scenario":
                response = build_scenario_response(payload)
            elif parsed.path == "/api/live-score":
                response = fetch_live_score()
            else:
                response = build_match_brief_response(payload)
            body = json.dumps(response).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:  # noqa: BLE001
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def main() -> None:
    ensure_dashboard_data()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Serving dashboard and scenario API at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
