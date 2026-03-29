from __future__ import annotations

import copy
import json
import os
import smtplib
import time
from email.mime.text import MIMEText
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

# ── Auth config ────────────────────────────────────────────────────────────────
_ACCESS_CODE    = (os.environ.get("RR_ACCESS_CODE") or "royals2026").strip()
_COOKIE_NAME    = "rr_auth"
_COOKIE_VALUE   = "creaseiq_ok"
# Paths served without authentication (GET)
_PUBLIC_PATHS      = {"/", "/index.html", "/rr_login.html", "/favicon.ico"}
# POST endpoints that don't require auth
_PUBLIC_POST_PATHS = {"/api/auth", "/api/demo-request"}

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
    # Only rebuild if not running as a Render web service (build step should have done it).
    # On Render, attempting to rebuild at startup would exceed the startup health-check timeout.
    if os.environ.get("RENDER"):
        print(
            "WARNING: dashboard_data.js missing on Render — skipping runtime rebuild. "
            "Re-deploy to trigger a fresh build.",
            flush=True,
        )
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
    model = str(payload.get("model") or os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured on the server")

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

    # Enrich context with live toss + playing XI when available.
    # fetch_match_context() is cached for 1 hour so it adds at most ~6 CricAPI
    # calls on a match day — safe within the free tier.
    match_context = fetch_match_context()
    if match_context:
        context["live_match_context"] = match_context

    system_prompt = (
        "You are a high-level IPL strategy analyst writing a match brief for a front-office decision-support dashboard. "
        "Use only the provided structured data. Do not invent statistics, players, venue traits, or matchup claims not present in the context. "
        "Be specific, tactical, and cricket-literate. Prefer realistic role language such as opener, enforcer, anchor, death hitter, new-ball bowler, and middle-overs controller. "
        "The live_match_context key (if present) contains today's toss result and confirmed playing XI — "
        "use these to make the brief specific to today's actual conditions rather than speaking generically. "
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
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
    }

    request = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent":    "python-requests/2.31.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload_raw = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Groq API error: {exc.code} {detail}") from exc
    except URLError as exc:
        raise ValueError(f"Unable to reach Groq API: {exc.reason}") from exc

    content = payload_raw["choices"][0]["message"]["content"].strip()
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

# Match-context cache: stores playing XI and toss for the current RR fixture.
# Refreshed at most once per hour (TTL = 3 600 s) so the match_info endpoint
# is called ~6 times per match day on the free CricAPI tier.
_match_context_cache: dict = {"match_id": None, "ts": 0.0, "data": None}
_MATCH_CONTEXT_TTL = 3600  # 1 hour


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


def fetch_match_context() -> dict:
    """
    Fetch playing XI and toss details for the current RR fixture from CricAPI.

    Uses a 1-hour cache keyed on the CricAPI match id so we call match_info
    at most ~6 times per match day.  Any error returns an empty dict (non-fatal
    — the match brief still works, just without live context).
    """
    global _match_context_cache

    api_key = os.environ.get("CRICAPI_KEY", "").strip()
    if not api_key:
        return {}

    now = time.time()

    # Step 1: Resolve the RR match id from currentMatches (uses same live-score
    # endpoint, which is already cached for 3 minutes independently).
    live_url = f"https://api.cricapi.com/v1/currentMatches?apikey={api_key}&offset=0"
    try:
        with urlopen(Request(live_url, method="GET"), timeout=10) as resp:
            current_payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[match_context] currentMatches fetch failed: {exc}", flush=True)
        return {}

    matches = current_payload.get("data", [])
    rr_match = next(
        (m for m in matches if any("rajasthan" in t.lower() for t in m.get("teams", []))),
        None,
    )
    if not rr_match:
        return {}

    match_id = rr_match.get("id")
    if not match_id:
        return {}

    # Step 2: Return cached context if it is still fresh for this same match
    if (
        _match_context_cache["match_id"] == match_id
        and _match_context_cache["data"] is not None
        and now - _match_context_cache["ts"] < _MATCH_CONTEXT_TTL
    ):
        return _match_context_cache["data"]

    # Step 3: Call match_info for the full playing XI and toss details
    info_url = f"https://api.cricapi.com/v1/match_info?apikey={api_key}&id={match_id}"
    try:
        with urlopen(Request(info_url, method="GET"), timeout=10) as resp:
            info_payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[match_context] match_info fetch failed: {exc}", flush=True)
        return {}

    info_data = info_payload.get("data", {})
    if not info_data:
        return {}

    toss_info   = info_data.get("tossResults", {}) or {}
    toss_winner  = toss_info.get("tossWinner", "")
    toss_decision = toss_info.get("decision", "")

    # playing XI may live under "players" (list-of-dicts) or "playerInfo"
    raw_players = info_data.get("players") or info_data.get("playerInfo") or {}
    playing_xi: dict = {}
    if isinstance(raw_players, dict):
        # keys are team names, values are lists of player dicts or plain names
        for team, player_list in raw_players.items():
            if isinstance(player_list, list):
                playing_xi[team] = [
                    p.get("name", p) if isinstance(p, dict) else str(p)
                    for p in player_list
                ]
    elif isinstance(raw_players, list):
        # Some API versions return a flat list with a "team" field per player
        for player in raw_players:
            team = player.get("team", "Unknown")
            playing_xi.setdefault(team, []).append(player.get("name", ""))

    context_data: dict = {
        "toss_winner":   toss_winner,
        "toss_decision": toss_decision,
        "playing_xi":    playing_xi,
        "match_name":    info_data.get("name", rr_match.get("name", "")),
    }

    _match_context_cache = {"match_id": match_id, "ts": now, "data": context_data}
    return context_data


_NOTIFY_EMAIL = "zpiyushrd19@gmail.com"


def handle_demo_request(payload: dict) -> dict:
    """Log a demo request and attempt to email a notification."""
    name  = str(payload.get("name",  "")).strip()[:120]
    email = str(payload.get("email", "")).strip()[:200]
    team  = str(payload.get("team",  "")).strip()[:120]
    note  = str(payload.get("note",  "")).strip()[:500]

    if not name or not email:
        raise ValueError("name and email are required")

    # Always log — visible in Render dashboard logs
    print(
        f"[DEMO REQUEST] name={name!r} email={email!r} team={team!r} note={note!r}",
        flush=True,
    )

    # Attempt email notification if Gmail app password is configured
    gmail_user     = os.environ.get("GMAIL_USER", "").strip()
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if gmail_user and gmail_password:
        try:
            body = (
                f"New CreaseIQ demo request\n\n"
                f"Name:  {name}\n"
                f"Email: {email}\n"
                f"Team:  {team or '(not specified)'}\n"
                f"Note:  {note or '(none)'}\n"
            )
            msg = MIMEText(body)
            msg["Subject"] = f"CreaseIQ demo request — {name}"
            msg["From"]    = gmail_user
            msg["To"]      = _NOTIFY_EMAIL
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(gmail_user, gmail_password)
                smtp.sendmail(gmail_user, _NOTIFY_EMAIL, msg.as_string())
        except Exception as exc:  # noqa: BLE001
            # Email failure is non-fatal — request is already logged above
            print(f"[DEMO REQUEST] email notification failed: {exc}", flush=True)

    return {"ok": True}


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    # ── Auth helpers ───────────────────────────────────────────────────────────
    def _is_authenticated(self) -> bool:
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == _COOKIE_NAME and v.strip() == _COOKIE_VALUE:
                return True
        return False

    def _redirect_to_login(self) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/rr_login.html")
        self.end_headers()

    def _send_json(self, status: HTTPStatus, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── GET ────────────────────────────────────────────────────────────────────
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # Normalise root
        if path in ("", "/"):
            path = "/index.html"

        # Always serve public pages without auth
        if path in _PUBLIC_PATHS:
            super().do_GET()
            return

        # Everything else requires a valid cookie
        if not self._is_authenticated():
            self._redirect_to_login()
            return

        if path == "/api/live-score":
            try:
                self._send_json(HTTPStatus.OK, fetch_live_score())
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        else:
            super().do_GET()

    # ── POST ───────────────────────────────────────────────────────────────────
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        allowed = {"/api/run-scenario", "/api/match-brief", "/api/live-score", "/api/auth", "/api/demo-request"}
        if parsed.path not in allowed:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8") or "{}")

            # Demo request — no cookie required (public landing page)
            if parsed.path == "/api/demo-request":
                self._send_json(HTTPStatus.OK, handle_demo_request(payload))
                return

            # Auth endpoint — no cookie required
            if parsed.path == "/api/auth":
                if payload.get("code") == _ACCESS_CODE:
                    body = json.dumps({"ok": True}).encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    # HttpOnly + SameSite=Strict keeps the cookie off JS and same-origin only
                    self.send_header(
                        "Set-Cookie",
                        f"{_COOKIE_NAME}={_COOKIE_VALUE}; Path=/; SameSite=Lax; HttpOnly; Max-Age=43200",
                    )
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False})
                return

            # All other API endpoints require auth
            if not self._is_authenticated():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Not authenticated"})
                return

            if parsed.path == "/api/run-scenario":
                response = build_scenario_response(payload)
            elif parsed.path == "/api/live-score":
                response = fetch_live_score()
            else:
                response = build_match_brief_response(payload)

            self._send_json(HTTPStatus.OK, response)

        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def main() -> None:
    ensure_dashboard_data()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Serving dashboard and scenario API at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
