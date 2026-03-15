from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path("/Users/piyushzaware/Documents/IPL_Data_Analysis")
DATA_DIR = ROOT / "Data"
OUT_DIR = ROOT / "Paper" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from Code.rr_auction_simulator import (
    TEAM_CONFIGS,
    build_team_states,
    canonical_player_name,
    normalize_name,
    resolve_team_configs,
)


def write_table(name: str, body: str) -> None:
    (OUT_DIR / name).write_text(body)


def latex_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def build_summary_table() -> None:
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv", parse_dates=["date"])
    rows = [
        ("Matches", f"{ball['match_id'].nunique():,}"),
        ("Deliveries", f"{len(ball):,}"),
        ("Batters", f"{ball['batter'].nunique():,}"),
        ("Bowlers", f"{ball['bowler'].nunique():,}"),
        ("Sample start", str(ball["date"].min().date())),
        ("Sample end", str(ball["date"].max().date())),
        ("Powerplay deliveries", f"{(ball['phase'] == 'powerplay').sum():,}"),
        ("Middle-over deliveries", f"{(ball['phase'] == 'middle').sum():,}"),
        ("Death-over deliveries", f"{(ball['phase'] == 'death').sum():,}"),
    ]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Ball-by-Ball IPL Sample}",
        r"\begin{tabular}{lc}",
        r"\toprule",
        r"Statistic & Value \\",
        r"\midrule",
    ]
    for stat, value in rows:
        lines.append(f"{latex_escape(stat)} & {latex_escape(value)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("sample_summary.tex", "\n".join(lines) + "\n")


def build_rr_core_table() -> None:
    files = {
        "pp_bat": ("Data/powerplay_batting_all_time.csv", "batter", "Batting PP"),
        "mid_bat": ("Data/middle_batting_all_time.csv", "batter", "Batting Mid"),
        "death_bat": ("Data/death_batting_all_time.csv", "batter", "Batting Death"),
        "pp_bowl": ("Data/powerplay_bowling_all_time.csv", "bowler", "Bowling PP"),
        "mid_bowl": ("Data/middle_bowling_all_time.csv", "bowler", "Bowling Mid"),
        "death_bowl": ("Data/death_bowling_all_time.csv", "bowler", "Bowling Death"),
    }
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv")
    rows = []
    for player in TEAM_CONFIGS["RR"]["retained_players"]:
        player_norm = normalize_name(player)
        found_rows = []
        for _, (path, col, label) in files.items():
            df = pd.read_csv(ROOT / path)
            df["rank"] = range(1, len(df) + 1)
            sub = df[df[col].astype(str).map(normalize_name) == player_norm]
            if not sub.empty:
                row = sub.iloc[0]
                found_rows.append((label, int(row["rank"])))

        if found_rows:
            found_rows.sort(key=lambda x: x[1])
            summary = "; ".join(f"{label}: {rank}" for label, rank in found_rows[:4])
            rows.append((canonical_player_name(player), "Observed", summary))
        else:
            batter_rows = ball[ball["batter"].astype(str).map(normalize_name) == player_norm]
            bowler_rows = ball[ball["bowler"].astype(str).map(normalize_name) == player_norm]
            if not batter_rows.empty or not bowler_rows.empty:
                details = []
                if not batter_rows.empty:
                    phase_balls = batter_rows.groupby("phase")["legal_ball"].sum().to_dict()
                    details.append(
                        "Batter sample balls: "
                        + ", ".join(f"{k} {int(v)}" for k, v in phase_balls.items())
                    )
                if not bowler_rows.empty:
                    phase_balls = bowler_rows.groupby("phase")["legal_ball"].sum().to_dict()
                    details.append(
                        "Bowler sample balls: "
                        + ", ".join(f"{k} {int(v)}" for k, v in phase_balls.items())
                    )
                rows.append((canonical_player_name(player), "Below cutoff", "; ".join(details)))
            else:
                rows.append((canonical_player_name(player), "No sample", "No public IPL ball-by-ball record in current dataset"))

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Phase-Ranking Evidence for All Retained RR Players}",
        r"\begin{tabular}{p{3.1cm}p{1.6cm}p{8.2cm}}",
        r"\toprule",
        r"Player & Coverage & Best Available Phase Rankings \\",
        r"\midrule",
    ]
    for player, coverage, summary in rows:
        lines.append(f"{latex_escape(player)} & {latex_escape(coverage)} & {latex_escape(summary)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("rr_core_rankings.tex", "\n".join(lines) + "\n")


def build_rr_retained_table() -> None:
    rr = TEAM_CONFIGS["RR"]
    players = rr["retained_players"]
    formatted = []
    for player in players:
        overseas = player in {
            "Donovan Ferreira", "Jofra Archer", "Kwena Maphaka",
            "Lhuan-Dre Pretorious", "Nandre Burger", "Sam Curran",
            "Shimron Hetmyer",
        }
        formatted.append((canonical_player_name(player), "Overseas" if overseas else "Domestic"))

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Rajasthan Royals Retained Squad Entering the 2026 Auction}",
        r"\begin{tabular}{ll}",
        r"\toprule",
        r"Player & Status \\",
        r"\midrule",
    ]
    for player, status in formatted:
        lines.append(f"{latex_escape(player)} & {latex_escape(status)} \\\\")
    lines += [
        r"\midrule",
        r"\multicolumn{2}{l}{Retained players: 16 \quad Overseas retained: 7} \\",
        r"\multicolumn{2}{l}{Total spent: Rs.\ 108.95 crore \quad Cap remaining: Rs.\ 16.05 crore} \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    write_table("rr_retained_squad.tex", "\n".join(lines) + "\n")


def build_team_power_table() -> None:
    states = build_team_states(resolve_team_configs("2026"))
    rows = []
    for code, state in states.items():
        rows.append(
            (
                code,
                state.retained,
                state.overseas_retained,
                state.purse,
                state.max_buys,
                state.aggression,
                state.auction_power,
            )
        )
    rows.sort(key=lambda x: x[-1], reverse=True)
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Franchise Auction Power in the Calibrated Model}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Team & Retained & Overseas & Purse & Open Slots & Aggression & Auction Power \\",
        r"\midrule",
    ]
    for code, retained, overseas, purse, open_slots, aggression, power in rows:
        lines.append(f"{code} & {retained} & {overseas} & {purse:.2f} & {open_slots} & {aggression:.2f} & {power:.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("team_auction_power.tex", "\n".join(lines) + "\n")


def build_rr_sim_table() -> None:
    df = pd.read_csv(DATA_DIR / "rr_auction_simulated_buys.csv")
    df["runner_up"] = df["runner_up"].fillna("--")
    df["role_bucket"] = df["role_bucket"].str.replace("_", " ").str.title()
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Simulated Rajasthan Royals Purchases}",
        r"\begin{tabular}{rllcc}",
        r"\toprule",
        r"Set & Player & Role Bucket & Final Price (Cr) & Runner-Up \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{int(row['set_no'])} & {latex_escape(row['player_name'])} & {latex_escape(row['role_bucket'])} & {row['final_price']:.2f} & {latex_escape(row['runner_up'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("rr_simulated_buys.tex", "\n".join(lines) + "\n")


def build_actual_compare_table() -> None:
    df = pd.read_csv(DATA_DIR / "rr_actual_vs_simulated.csv")
    df["simulated"] = df["simulated"].map({True: "Yes", False: "No"})
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Observed and Simulated Core RR Targets}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"Player & Actual Auction Note & Simulated Match \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{latex_escape(row['actual_player'])} & {latex_escape(row['actual_note'])} & {latex_escape(row['simulated'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("rr_actual_compare.tex", "\n".join(lines) + "\n")


def build_mc_summary_table() -> None:
    df = pd.read_csv(DATA_DIR / "rr_auction_purchase_summary_2026_mc.csv")
    keep = ["Ravi Bishnoi", "Rahul Chahar", "Adam Milne", "Chetan Sakariya"]
    df = df[df["player_name"].isin(keep)].copy()
    order = {name: i for i, name in enumerate(keep)}
    df["sort_key"] = df["player_name"].map(order)
    df = df.sort_values("sort_key").drop(columns=["sort_key"])
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Randomized Within-Set Monte Carlo Outcomes for Key RR Targets}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Player & Purchase Share & Times Bought & Avg. Price When Bought (Cr) \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{latex_escape(row['player_name'])} & {float(row['share_of_runs']):.3f} & {int(row['times_bought'])} & {float(row['avg_price_when_bought']):.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("rr_mc_summary.tex", "\n".join(lines) + "\n")


def build_key_events_table() -> None:
    events = pd.read_csv(DATA_DIR / "auction_simulation_2026_events.csv")
    keep = ["Ravi Bishnoi", "Adam Milne", "Fazalhaq Farooqi", "Kyle Jamieson"]
    df = events[events["player_name"].isin(keep)].copy()
    df["winner"] = df["winner"].fillna("--")
    df["final_price"] = df["final_price"].fillna("--")
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Selected Auction Outcomes Relevant for RR Strategy}",
        r"\begin{tabular}{rllcc}",
        r"\toprule",
        r"Set & Player & Winner & Final Price (Cr) & RR Bid Cap \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        final_price = row["final_price"] if row["final_price"] == "--" else f"{float(row['final_price']):.2f}"
        lines.append(
            f"{int(row['set_no'])} & {latex_escape(row['player_name'])} & {latex_escape(row['winner'])} & {final_price} & {float(row['focus_team_bid_cap']):.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write_table("rr_key_events.tex", "\n".join(lines) + "\n")


def main() -> None:
    build_summary_table()
    build_rr_retained_table()
    build_rr_core_table()
    build_team_power_table()
    build_rr_sim_table()
    build_actual_compare_table()
    build_mc_summary_table()
    build_key_events_table()
    print("Generated tables in", OUT_DIR)


if __name__ == "__main__":
    main()
