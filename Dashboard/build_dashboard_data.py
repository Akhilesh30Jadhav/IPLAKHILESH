from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"
DASHBOARD_DIR = ROOT / "Dashboard"
OUT_DIR = DASHBOARD_DIR / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from Code.rr_auction_simulator import (
    add_player_valuation_columns,
    build_team_states,
    canonical_player_name,
    load_auction_pool,
    normalize_name,
    resolve_team_configs,
)


PHASE_FILES = {
    "batting": {
        "powerplay": DATA_DIR / "powerplay_batting_all_time.csv",
        "middle": DATA_DIR / "middle_batting_all_time.csv",
        "death": DATA_DIR / "death_batting_all_time.csv",
    },
    "bowling": {
        "powerplay": DATA_DIR / "powerplay_bowling_all_time.csv",
        "middle": DATA_DIR / "middle_bowling_all_time.csv",
        "death": DATA_DIR / "death_bowling_all_time.csv",
    },
}

ACTIVE_PHASE_FILES = {
    "batting": {
        "powerplay": DATA_DIR / "powerplay_batting_active.csv",
        "middle": DATA_DIR / "middle_batting_active.csv",
        "death": DATA_DIR / "death_batting_active.csv",
    },
    "bowling": {
        "powerplay": DATA_DIR / "powerplay_bowling_active.csv",
        "middle": DATA_DIR / "middle_bowling_active.csv",
        "death": DATA_DIR / "death_bowling_active.csv",
    },
}

PHASE_ORDER = ["powerplay", "middle", "death"]
ACTIVE_CUTOFF_YEAR = 2025


def ensure_auction_outputs() -> None:
    required_paths = [DATA_DIR / "league_auction_mc_summary_2026.csv", DATA_DIR / "league_auction_simulation_2026_events.csv"]
    team_codes = sorted(resolve_team_configs("2026").keys())
    for code in team_codes:
        slug = code.lower()
        required_paths.extend(
            [
                DATA_DIR / f"{slug}_auction_simulated_buys_2026.csv",
                DATA_DIR / f"{slug}_auction_purchase_summary_2026_mc.csv",
                DATA_DIR / f"{slug}_auction_spend_summary_2026_mc.csv",
            ]
        )
    if all(path.exists() for path in required_paths):
        return

    from Code.run_league_monte_carlo import main as run_league_monte_carlo_main

    print("Auction outputs missing. Generating league simulation artifacts...")
    run_league_monte_carlo_main()


def top_records(df: pd.DataFrame, name_col: str, columns: list[str], top_n: int = 12) -> list[dict]:
    trimmed = df.head(top_n).copy()
    rows = []
    for idx, row in trimmed.iterrows():
        payload = {"rank": idx + 1, "player": canonical_player_name(str(row[name_col]))}
        for column in columns:
            value = row[column]
            if pd.isna(value):
                payload[column] = None
            elif isinstance(value, (int, float)):
                payload[column] = round(float(value), 2)
            else:
                payload[column] = value
        rows.append(payload)
    return rows


def all_records(df: pd.DataFrame, name_col: str, columns: list[str]) -> list[dict]:
    rows = []
    for idx, row in df.reset_index(drop=True).iterrows():
        payload = {"rank": idx + 1, "player": canonical_player_name(str(row[name_col]))}
        for column in columns:
            value = row[column]
            if pd.isna(value):
                payload[column] = None
            elif isinstance(value, (int, float)):
                payload[column] = round(float(value), 2)
            else:
                payload[column] = value
        rows.append(payload)
    return rows


def build_phase_payload() -> dict:
    payload: dict[str, dict[str, list[dict]]] = {"all_time": {}, "active": {}}
    for horizon, file_map in [("all_time", PHASE_FILES), ("active", PHASE_FILES)]:
        for discipline, phase_map in file_map.items():
            for phase, path in phase_map.items():
                df = pd.read_csv(path).sort_values("impact_score", ascending=False).reset_index(drop=True)
                if horizon == "active":
                    df = df[df["last_year"] >= ACTIVE_CUTOFF_YEAR].copy()
                    df = df.sort_values("impact_score", ascending=False).reset_index(drop=True)
                name_col = "batter" if discipline == "batting" else "bowler"
                metrics = (
                    ["runs", "balls", "strike_rate", "sr_bayes", "impact_score", "last_year"]
                    if discipline == "batting"
                    else ["runs", "balls", "wickets", "economy", "econ_bayes", "impact_score", "last_year"]
                )
                payload[horizon][f"{discipline}_{phase}"] = all_records(df, name_col, metrics)
    return payload


def build_overview_payload() -> dict:
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv", parse_dates=["date"])
    league = pd.read_csv(DATA_DIR / "league_auction_mc_summary_2026.csv")
    return {
        "matches": int(ball["match_id"].nunique()),
        "deliveries": int(len(ball)),
        "batters": int(ball["batter"].nunique()),
        "bowlers": int(ball["bowler"].nunique()),
        "sample_start": str(ball["date"].min().date()),
        "sample_end": str(ball["date"].max().date()),
        "teams_simulated": int(len(league)),
        "league_top_budget_team": str(league.iloc[0]["team_code"]),
        "league_avg_spend": round(float(league["mc_average_spend"].mean()), 2),
        "league_max_target_share": round(float(league["mc_top_target_share"].max()), 3),
    }


def build_auction_payload() -> dict:
    teams_payload = {}
    league_summary_df = pd.read_csv(DATA_DIR / "league_auction_mc_summary_2026.csv")
    if "mc_top_target" in league_summary_df.columns:
        league_summary_df["mc_top_target"] = league_summary_df["mc_top_target"].fillna("").map(canonical_player_name).replace({"": None})
    league_summary = league_summary_df.to_dict("records")
    league_events = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events.csv")
    for col in ["player_name", "winner", "runner_up"]:
        if col in league_events.columns:
            league_events[col] = league_events[col].fillna("").map(canonical_player_name).replace({"": None})
    replay_events = league_events.copy()
    replay_events["sequence_no"] = range(1, len(replay_events) + 1)
    filtered_events = league_events[
        [
            "set_no",
            "player_name",
            "role_bucket",
            "reserve_price",
            "winner",
            "final_price",
            "runner_up",
            "quality_score",
        ]
    ].copy()
    filtered_events = filtered_events.sort_values(["set_no", "final_price"], ascending=[True, False]).head(200)
    for team_code in sorted(resolve_team_configs("2026").keys()):
        slug = team_code.lower()
        buys = pd.read_csv(DATA_DIR / f"{slug}_auction_simulated_buys_2026.csv")
        mc = pd.read_csv(DATA_DIR / f"{slug}_auction_purchase_summary_2026_mc.csv")
        spend_mc = pd.read_csv(DATA_DIR / f"{slug}_auction_spend_summary_2026_mc.csv")
        buys = buys.assign(
            player_name=buys["player_name"].map(canonical_player_name),
            runner_up=buys["runner_up"].fillna("").map(canonical_player_name).replace({"": None}),
        )
        mc = mc.assign(player_name=mc["player_name"].map(canonical_player_name))

        teams_payload[team_code] = {
            "single_run_buys": buys.to_dict("records"),
            "mc_purchase_summary": mc.to_dict("records"),
            "mc_spend_summary": spend_mc.to_dict("records"),
            "top_targets": mc.head(6).to_dict("records"),
        }

    return {
        "mode": "shared_league_simulation",
        "league_summary": league_summary,
        "league_events": filtered_events.to_dict("records"),
        "replay_events": replay_events.to_dict("records"),
        "teams": teams_payload,
    }


def build_team_payload() -> dict:
    configs = resolve_team_configs("2026")
    states = build_team_states(configs)
    teams = []
    for code, config in configs.items():
        state = states[code]
        teams.append(
            {
                "code": code,
                "name": config["name"],
                "purse": config["purse"],
                "spent": config["spent"],
                "retained": config["retained"],
                "overseas_retained": config["overseas_retained"],
                "retained_players": [canonical_player_name(player) for player in config["retained_players"]],
                "role_needs": config.get("role_needs", {}),
                "role_caps": config.get("role_caps", {}),
                "auction_power": state.auction_power,
                "aggression": state.aggression,
                "open_slots": max(0, state.squad_size - state.retained),
                "overseas_slots_left": max(0, state.overseas_limit - state.overseas_retained),
            }
        )
    teams.sort(key=lambda item: item["auction_power"], reverse=True)
    return {"teams_2026": teams}


def safe_float(value: object) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)


def safe_int(value: object) -> int:
    if pd.isna(value):
        return 0
    return int(value)


def bowl_family_from_style(style: object) -> str | None:
    text = str(style or "").upper()
    if not text:
        return None
    spin_terms = ["SPIN", "ORTHODOX", "UNORTHODOX", "SLOW", "CHINAMAN"]
    if any(term in text for term in spin_terms):
        return "Spin"
    return "Pace"


def percentile_map(series: pd.Series, ascending: bool = True) -> dict[str, float]:
    ranked = series.rank(pct=True, ascending=ascending)
    return {str(index): round(float(value) * 100, 1) for index, value in ranked.items()}


def build_player_payload() -> dict:
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv", parse_dates=["date"])
    ball["run_value"] = ball["runs_total"] - ball["runs_total"].mean()

    batter_base = (
        ball.groupby("batter")
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            last_year=("date", lambda values: int(pd.to_datetime(values).dt.year.max())),
            matches=("match_id", "nunique"),
            run_value=("run_value", "sum"),
        )
        .reset_index()
        .rename(columns={"batter": "player"})
    )
    batter_base["strike_rate"] = (batter_base["runs"] / batter_base["balls"].clip(lower=1)) * 100
    batter_base["wins_added"] = batter_base["run_value"] / 15.0

    bowler_base = (
        ball.groupby("bowler")
        .agg(
            runs=("runs_total", "sum"),
            balls=("legal_ball", "sum"),
            wickets=("wicket", "sum"),
            last_year=("date", lambda values: int(pd.to_datetime(values).dt.year.max())),
            matches=("match_id", "nunique"),
            run_value=("run_value", "sum"),
        )
        .reset_index()
        .rename(columns={"bowler": "player"})
    )
    bowler_base["economy"] = bowler_base["runs"] / (bowler_base["balls"].clip(lower=1) / 6.0)
    bowler_base["wins_added"] = -bowler_base["run_value"] / 15.0

    batter_phase_frames = {phase: pd.read_csv(path) for phase, path in PHASE_FILES["batting"].items()}
    bowler_phase_frames = {phase: pd.read_csv(path) for phase, path in PHASE_FILES["bowling"].items()}

    batter_pp_impact = percentile_map(
        batter_phase_frames["powerplay"].set_index("batter")["impact_score"], ascending=True
    )
    batter_mid_impact = percentile_map(
        batter_phase_frames["middle"].set_index("batter")["impact_score"], ascending=True
    )
    batter_death_impact = percentile_map(
        batter_phase_frames["death"].set_index("batter")["impact_score"], ascending=True
    )
    batter_volume_pct = percentile_map(batter_base.set_index("player")["balls"], ascending=True)
    batter_sr_pct = percentile_map(batter_base.set_index("player")["strike_rate"], ascending=True)
    batter_win_pct = percentile_map(batter_base.set_index("player")["wins_added"], ascending=True)

    bowler_pp_impact = percentile_map(
        bowler_phase_frames["powerplay"].set_index("bowler")["impact_score"], ascending=True
    )
    bowler_mid_impact = percentile_map(
        bowler_phase_frames["middle"].set_index("bowler")["impact_score"], ascending=True
    )
    bowler_death_impact = percentile_map(
        bowler_phase_frames["death"].set_index("bowler")["impact_score"], ascending=True
    )
    bowler_workload_pct = percentile_map(bowler_base.set_index("player")["balls"], ascending=True)
    bowler_wicket_pct = percentile_map(bowler_base.set_index("player")["wickets"], ascending=True)
    bowler_control_pct = percentile_map(bowler_base.set_index("player")["economy"], ascending=False)

    batter_profiles = {}
    for _, row in batter_base.sort_values("runs", ascending=False).iterrows():
        player = row["player"]
        display_player = canonical_player_name(str(player))
        phase_details = {}
        total_impact_score = 0.0
        for phase in PHASE_ORDER:
            frame = batter_phase_frames[phase]
            sub = frame[frame["batter"] == player]
            if sub.empty:
                phase_details[phase] = {"impact_score": 0.0, "balls": 0, "sr_bayes": 0.0}
            else:
                record = sub.iloc[0]
                impact_score = round(safe_float(record["impact_score"]), 2)
                phase_details[phase] = {
                    "impact_score": impact_score,
                    "balls": int(safe_float(record["balls"])),
                    "sr_bayes": round(safe_float(record["sr_bayes"]), 2),
                }
                total_impact_score += impact_score

        batter_profiles[display_player] = {
            "player": display_player,
            "type": "batter",
            "summary": {
                "runs": int(safe_float(row["runs"])),
                "balls": int(safe_float(row["balls"])),
                "strike_rate": round(safe_float(row["strike_rate"]), 2),
                "matches": int(safe_float(row["matches"])),
                "last_year": int(safe_float(row["last_year"])),
                "run_value": round(safe_float(row["run_value"]), 2),
                "wins_added": round(safe_float(row["wins_added"]), 2),
                "impact_score": round(total_impact_score, 2),
            },
            "phase_details": phase_details,
            "radar": [
                {"axis": "PP Impact", "value": batter_pp_impact.get(player, 0.0)},
                {"axis": "Middle Impact", "value": batter_mid_impact.get(player, 0.0)},
                {"axis": "Death Impact", "value": batter_death_impact.get(player, 0.0)},
                {"axis": "Volume", "value": batter_volume_pct.get(player, 0.0)},
                {"axis": "Strike Rate", "value": batter_sr_pct.get(player, 0.0)},
                {"axis": "Wins Added", "value": batter_win_pct.get(player, 0.0)},
            ],
        }

    bowler_profiles = {}
    for _, row in bowler_base.sort_values("wickets", ascending=False).iterrows():
        player = row["player"]
        display_player = canonical_player_name(str(player))
        phase_details = {}
        total_impact_score = 0.0
        for phase in PHASE_ORDER:
            frame = bowler_phase_frames[phase]
            sub = frame[frame["bowler"] == player]
            if sub.empty:
                phase_details[phase] = {"impact_score": 0.0, "balls": 0, "econ_bayes": 0.0, "wickets": 0}
            else:
                record = sub.iloc[0]
                impact_score = round(safe_float(record["impact_score"]), 2)
                phase_details[phase] = {
                    "impact_score": impact_score,
                    "balls": int(safe_float(record["balls"])),
                    "econ_bayes": round(safe_float(record["econ_bayes"]), 2),
                    "wickets": int(safe_float(record["wickets"])),
                }
                total_impact_score += impact_score

        bowler_profiles[display_player] = {
            "player": display_player,
            "type": "bowler",
            "summary": {
                "runs": int(safe_float(row["runs"])),
                "balls": int(safe_float(row["balls"])),
                "economy": round(safe_float(row["economy"]), 2),
                "wickets": int(safe_float(row["wickets"])),
                "matches": int(safe_float(row["matches"])),
                "last_year": int(safe_float(row["last_year"])),
                "run_value": round(safe_float(row["run_value"]), 2),
                "wins_added": round(safe_float(row["wins_added"]), 2),
                "impact_score": round(total_impact_score, 2),
            },
            "phase_details": phase_details,
            "radar": [
                {"axis": "PP Impact", "value": bowler_pp_impact.get(player, 0.0)},
                {"axis": "Middle Impact", "value": bowler_mid_impact.get(player, 0.0)},
                {"axis": "Death Impact", "value": bowler_death_impact.get(player, 0.0)},
                {"axis": "Workload", "value": bowler_workload_pct.get(player, 0.0)},
                {"axis": "Wickets", "value": bowler_wicket_pct.get(player, 0.0)},
                {"axis": "Control", "value": bowler_control_pct.get(player, 0.0)},
            ],
        }

    top_batter_impact = (
        pd.DataFrame(
            [
                {
                    "player": profile["player"],
                    "impact_score": profile["summary"]["impact_score"],
                    "wins_added": profile["summary"]["wins_added"],
                    "run_value": profile["summary"]["run_value"],
                    "runs": profile["summary"]["runs"],
                    "strike_rate": profile["summary"]["strike_rate"],
                    "last_year": profile["summary"]["last_year"],
                }
                for profile in batter_profiles.values()
            ]
        )
        .sort_values("impact_score", ascending=False)
        .head(40)
        .to_dict("records")
    )
    top_bowler_impact = (
        pd.DataFrame(
            [
                {
                    "player": profile["player"],
                    "impact_score": profile["summary"]["impact_score"],
                    "wins_added": profile["summary"]["wins_added"],
                    "run_value": profile["summary"]["run_value"],
                    "wickets": profile["summary"]["wickets"],
                    "economy": profile["summary"]["economy"],
                    "last_year": profile["summary"]["last_year"],
                }
                for profile in bowler_profiles.values()
            ]
        )
        .sort_values("impact_score", ascending=False)
        .head(40)
        .to_dict("records")
    )

    return {
        "batter_options": sorted(batter_profiles.keys()),
        "bowler_options": sorted(bowler_profiles.keys()),
        "batter_profiles": batter_profiles,
        "bowler_profiles": bowler_profiles,
        "top_batter_impact": top_batter_impact,
        "top_bowler_impact": top_bowler_impact,
        "methodology": {
            "skill_radar": {
                "title": "Skill Radar Construction",
                "text": (
                    "The radar charts convert project outputs into percentile-style skill profiles. "
                    "For batters, the axes combine powerplay, middle, and death phase impact with overall volume, strike rate, "
                    "and wins-added contribution. For bowlers, the axes combine phase impact with workload, wicket-taking, "
                    "and economy control. This makes radar comparisons intuitive across specialist roles."
                ),
            },
            "impact_scores": {
                "title": "Impact Score Construction",
                "text": (
                    "Batting impact follows the notebook formula impact = sr_bayes x balls, where sr_bayes is the Bayesian-shrunk "
                    "phase strike rate. Bowling impact follows impact = (league_econ - econ_bayes) x balls + wicket_weight x wickets. "
                    "These scores reward both quality and credible sample size."
                ),
            },
            "wpa": {
                "title": "WPA / Wins-Added Construction",
                "text": (
                    "The notebook sketches a run-expectancy based framework: state variables such as overs remaining and wickets remaining "
                    "define expected future runs, each ball gets run value = actual runs - expected runs, player contributions aggregate these "
                    "run values, and wins added is approximated using 15 runs about 1 win. In the current codebase, the implemented proxy uses "
                    "run_value = runs_total - mean(runs_total) and wins_added = run_value_sum / 15. This is best read as a tractable wins-added proxy, "
                    "not yet a fully structural win-probability model."
                ),
            },
        },
    }


def build_scenario_payload() -> dict:
    team_configs = resolve_team_configs("2026")
    states = build_team_states(team_configs)
    auction_pool = add_player_valuation_columns(load_auction_pool("2026"), season="2026")
    league_events = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events.csv")

    event_lookup = (
        league_events.assign(player_name=league_events["player_name"].map(canonical_player_name)).drop_duplicates("player_name")
        .set_index("player_name")[["winner", "final_price", "runner_up", "set_no"]]
        .to_dict("index")
    )

    players = []
    for _, row in auction_pool.iterrows():
        player_name = canonical_player_name(str(row["player_name"]))
        rep = event_lookup.get(player_name, {})
        players.append(
            {
                "player_name": player_name,
                "role_bucket": row["role_bucket"],
                "reserve_price": round(float(row["reserve_price"]), 2),
                "quality_score": round(float(row["quality_score"]), 4),
                "base_ceiling": round(float(row["base_ceiling"]), 2),
                "set_no": safe_int(rep.get("set_no", row["set_no"])),
                "winner": rep.get("winner"),
                "final_price": None if pd.isna(rep.get("final_price")) else round(float(rep.get("final_price")), 2),
                "runner_up": rep.get("runner_up"),
                "is_overseas": bool(row["is_overseas"]),
                "bowl_family": bowl_family_from_style(row.get("bowl_style")),
                "bat_hand": str(row.get("bat_style") or "").upper() or None,
            }
        )

    players_df = pd.DataFrame(players)
    team_payload = {}
    for code, config in sorted(team_configs.items()):
        slug = code.lower()
        mc_path = DATA_DIR / f"{slug}_auction_purchase_summary_2026_mc.csv"
        mc_df = pd.read_csv(mc_path) if mc_path.exists() else pd.DataFrame(columns=["player_name", "share_of_runs"])
        mc_share_map = mc_df.set_index("player_name")["share_of_runs"].to_dict() if not mc_df.empty else {}
        top_targets = (
            players_df.assign(mc_share=players_df["player_name"].map(mc_share_map).fillna(0.0))
            .sort_values(["mc_share", "quality_score"], ascending=[False, False])
            .head(20)
        )

        state = states[code]
        team_payload[code] = {
            "name": config["name"],
            "purse": config["purse"],
            "spent": config["spent"],
            "retained": config["retained"],
            "overseas_retained": config["overseas_retained"],
            "retained_players": [canonical_player_name(player) for player in config["retained_players"]],
            "open_slots": max(0, state.squad_size - state.retained),
            "overseas_slots_left": max(0, state.overseas_limit - state.overseas_retained),
            "auction_power": state.auction_power,
            "aggression": state.aggression,
            "role_caps": config.get("role_caps", {}),
            "role_needs": config.get("role_needs", {}),
            "top_targets": top_targets[
                ["player_name", "role_bucket", "reserve_price", "quality_score", "base_ceiling", "mc_share", "is_overseas"]
            ].to_dict("records"),
            "mc_share_map": {name: round(float(value), 3) for name, value in mc_share_map.items()},
        }

    return {
        "teams": team_payload,
        "players": players_df.sort_values(["quality_score", "reserve_price"], ascending=[False, False]).to_dict("records"),
        "methodology": {
            "title": "Scenario Builder Logic",
            "text": (
                "This is a lightweight front-end general-equilibrium auction layer built on the calibrated 2026 auction pool. "
                "Users can change one team's purse, retained structure, overseas flexibility, and role priorities, then rerun a shared league auction "
                "where rival teams still bid under their own constraints. The output is therefore a market-clearing counterfactual rather than a simple "
                "partial-equilibrium ranking of isolated targets."
            )
        },
    }


def build_matchup_payload() -> dict:
    ball = pd.read_csv(
        DATA_DIR / "ipl_ball_by_ball.csv",
        usecols=[
            "batter",
            "bowler",
            "phase",
            "runs_batter",
            "runs_total",
            "wicket",
            "legal_ball",
            "balls_remaining",
            "innings_wickets_cum",
        ],
    )
    auction_pool = add_player_valuation_columns(load_auction_pool("2026"), season="2026")
    player_meta = (
        auction_pool.sort_values(["player_name"])
        .drop_duplicates("player_name")
        .assign(player_norm=lambda frame: frame["player_name"].map(normalize_name))
    )
    bat_style_map = player_meta.set_index("player_norm")["bat_style"].astype(str).to_dict()
    bowl_style_map = player_meta.set_index("player_norm")["bowl_style"].astype(str).to_dict()

    ball = ball.copy()
    ball["batter_norm"] = ball["batter"].map(normalize_name)
    ball["bowler_norm"] = ball["bowler"].map(normalize_name)
    ball["batter_hand"] = ball["batter_norm"].map(bat_style_map).replace({"": None})
    ball["bowler_style"] = ball["bowler_norm"].map(bowl_style_map).replace({"": None})
    ball["bowl_family"] = ball["bowler_style"].map(bowl_family_from_style)
    ball["pressure_state"] = (
        (ball["balls_remaining"] <= 30) | (ball["innings_wickets_cum"] >= 5)
    ).map({True: "High Pressure", False: "Standard"})

    matchup_ball = ball[ball["bowl_family"].notna()].copy()
    batter_vs_style = (
        matchup_ball.groupby(["batter", "bowl_family"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), dismissals=("wicket", "sum"))
        .reset_index()
    )
    batter_vs_style = batter_vs_style[batter_vs_style["balls"] >= 20].copy()
    batter_vs_style["strike_rate"] = (batter_vs_style["runs"] / batter_vs_style["balls"].clip(lower=1)) * 100.0

    hand_ball = ball[ball["batter_hand"].isin(["LHB", "RHB"])].copy()
    bowler_vs_hand = (
        hand_ball.groupby(["bowler", "batter_hand", "phase"])
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"))
        .reset_index()
    )
    bowler_vs_hand = bowler_vs_hand[bowler_vs_hand["balls"] >= 18].copy()
    bowler_vs_hand["economy"] = bowler_vs_hand["runs"] / (bowler_vs_hand["balls"].clip(lower=1) / 6.0)

    pressure_batting = (
        ball.groupby(["batter", "pressure_state"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), dismissals=("wicket", "sum"))
        .reset_index()
    )
    pressure_batting = pressure_batting[pressure_batting["balls"] >= 20].copy()
    pressure_batting["strike_rate"] = (pressure_batting["runs"] / pressure_batting["balls"].clip(lower=1)) * 100.0

    pressure_bowling = (
        ball.groupby(["bowler", "pressure_state"])
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"))
        .reset_index()
    )
    pressure_bowling = pressure_bowling[pressure_bowling["balls"] >= 18].copy()
    pressure_bowling["economy"] = pressure_bowling["runs"] / (pressure_bowling["balls"].clip(lower=1) / 6.0)

    head_to_head_total = (
        ball.groupby(["batter", "bowler"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), dismissals=("wicket", "sum"))
        .reset_index()
    )
    head_to_head_total = head_to_head_total[head_to_head_total["balls"] >= 1].copy()
    head_to_head_total["strike_rate"] = (head_to_head_total["runs"] / head_to_head_total["balls"].clip(lower=1)) * 100.0

    head_to_head_phase = (
        ball.groupby(["batter", "bowler", "phase"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), dismissals=("wicket", "sum"))
        .reset_index()
    )
    head_to_head_phase = head_to_head_phase[head_to_head_phase["balls"] >= 1].copy()
    head_to_head_phase["strike_rate"] = (head_to_head_phase["runs"] / head_to_head_phase["balls"].clip(lower=1)) * 100.0

    batter_phase_profiles: dict[str, dict[str, dict[str, float]]] = {}
    bowler_phase_profiles: dict[str, dict[str, dict[str, float]]] = {}
    for phase in PHASE_ORDER:
        bat_frame = pd.read_csv(PHASE_FILES["batting"][phase]).copy()
        bowl_frame = pd.read_csv(PHASE_FILES["bowling"][phase]).copy()

        bat_percentiles = bat_frame["impact_score"].rank(pct=True) * 100.0
        bowl_percentiles = bowl_frame["impact_score"].rank(pct=True) * 100.0
        bat_frame["impact_pct"] = bat_percentiles
        bowl_frame["impact_pct"] = bowl_percentiles

        for _, row in bat_frame.iterrows():
            batter_phase_profiles.setdefault(canonical_player_name(str(row["batter"])), {})[phase] = {
                "impact_score": round(float(row["impact_score"]), 2),
                "impact_pct": round(float(row["impact_pct"]), 2),
                "balls": safe_int(row["balls"]),
                "sr_bayes": round(float(row["sr_bayes"]), 2),
            }
        for _, row in bowl_frame.iterrows():
            bowler_phase_profiles.setdefault(canonical_player_name(str(row["bowler"])), {})[phase] = {
                "impact_score": round(float(row["impact_score"]), 2),
                "impact_pct": round(float(row["impact_pct"]), 2),
                "balls": safe_int(row["balls"]),
                "econ_bayes": round(float(row["econ_bayes"]), 2),
                "wickets": safe_int(row["wickets"]),
            }

    death_batting = pd.read_csv(PHASE_FILES["batting"]["death"]).sort_values("impact_score", ascending=False).head(20)
    death_bowling = pd.read_csv(PHASE_FILES["bowling"]["death"]).sort_values("impact_score", ascending=False).head(20)

    for frame, name_col in [
        (batter_vs_style, "batter"),
        (bowler_vs_hand, "bowler"),
        (pressure_batting, "batter"),
        (pressure_bowling, "bowler"),
        (head_to_head_total, "batter"),
        (head_to_head_total, "bowler"),
        (head_to_head_phase, "batter"),
        (head_to_head_phase, "bowler"),
        (death_batting, "batter"),
        (death_bowling, "bowler"),
    ]:
        frame[name_col] = frame[name_col].map(canonical_player_name)

    return {
        "batter_options": sorted(batter_vs_style["batter"].unique().tolist()),
        "bowler_options": sorted(bowler_vs_hand["bowler"].unique().tolist()),
        "batter_vs_style": batter_vs_style.to_dict("records"),
        "bowler_vs_hand": bowler_vs_hand.to_dict("records"),
        "pressure_batting": pressure_batting.to_dict("records"),
        "pressure_bowling": pressure_bowling.to_dict("records"),
        "head_to_head_total": head_to_head_total.to_dict("records"),
        "head_to_head_phase": head_to_head_phase.to_dict("records"),
        "batter_phase_profiles": batter_phase_profiles,
        "bowler_phase_profiles": bowler_phase_profiles,
        "death_specialists": {
            "batting": death_batting[["batter", "impact_score", "balls", "sr_bayes"]].to_dict("records"),
            "bowling": death_bowling[["bowler", "impact_score", "balls", "econ_bayes", "wickets"]].to_dict("records"),
        },
        "methodology": {
            "matchups": (
                "Matchup Intelligence combines ball-by-ball outcomes with player-style metadata from the 2026 auction workbook. "
                "Batters are split by pace versus spin when bowler styles can be matched reliably. Bowlers are split by phase and "
                "batting handedness when batter-hand data is available."
            ),
            "pressure": (
                "Pressure states are defined as deliveries with 30 or fewer balls remaining or innings wicket count of at least five. "
                "This isolates late-innings and collapse-style scenarios where decision value is highest."
            ),
            "contest_engine": (
                "The live matchup engine blends three ingredients by phase: the batter's phase impact percentile, the bowler's phase impact "
                "percentile, and any direct head-to-head evidence for that batter-bowler pair in the same phase. This creates an interactive, "
                "instant contest read rather than a static descriptive table."
            ),
            "death": (
                "Death-over specialists are taken from the notebook's Bayesian death-phase rankings, preserving the impact construction "
                "already used elsewhere in the project."
            ),
        },
    }


def build_story_payload() -> dict:
    return {
        "hero_title": "IPL Auction Intelligence League Hub",
        "hero_subtitle": (
            "A business-intelligence style dashboard for phase-based player value, "
            "team-level auction strategy, and a shared league-wide Monte Carlo auction simulation."
        ),
        "sections": [
            {
                "title": "Phase Analytics",
                "text": "Track powerplay, middle, and death specialists using Bayesian-adjusted impact signals from the ball-by-ball model.",
            },
            {
                "title": "League Auction Strategy",
                "text": "See how reserve prices, role scarcity, walk-away caps, and retained cores shape bidding logic inside one shared league auction rather than disconnected team counterfactuals.",
            },
            {
                "title": "Sequential Risk",
                "text": "Compare single-path auction outcomes with 500 randomized within-set simulations for every franchise to understand order sensitivity.",
            },
        ],
    }


def main() -> None:
    ensure_auction_outputs()
    payload = {
        "overview": build_overview_payload(),
        "phase_rankings": build_phase_payload(),
        "auction": build_auction_payload(),
        "teams": build_team_payload(),
        "players": build_player_payload(),
        "scenario": build_scenario_payload(),
        "matchups": build_matchup_payload(),
        "story": build_story_payload(),
    }
    js = "window.DASHBOARD_DATA = " + json.dumps(payload, indent=2) + ";\n"
    (OUT_DIR / "dashboard_data.js").write_text(js)
    print("Wrote", OUT_DIR / "dashboard_data.js")


if __name__ == "__main__":
    main()
