from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
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
    first_initial_key,
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
PLAYING_XI_OVERSEAS_LIMIT = 4
LOCKED_XI_PLAYERS = {
    "RR": {
        "Riyan Parag": "captain",
        "Ravindra Jadeja": "star all-rounder",
    }
}
RETAINED_OVERSEAS_PLAYERS = {
    "RR": {
        "Donovan Ferreira",
        "Jofra Archer",
        "Kwena Maphaka",
        "Lhuan-Dre Pretorious",
        "Nandre Burger",
        "Sam Curran",
        "Shimron Hetmyer",
    },
    "CSK": {"Jamie Overton", "Nathan Ellis", "Noor Ahmad", "Dewald Brevis"},
    "DC": {"Dushmantha Chameera", "Mitchell Starc", "Tristan Stubbs"},
    "GT": {"Glenn Phillips", "Jos Buttler", "Kagiso Rabada", "Rashid Khan"},
    "KKR": {"Rovman Powell", "Sunil Narine"},
    "LSG": {"Aiden Markram", "Matthew Breetzke", "Mitchell Marsh", "Nicholas Pooran"},
    "MI": {"Allah Ghazanfar", "Corbin Bosch", "Mitchell Santner", "Ryan Rickelton", "Sherfane Rutherford", "Trent Boult", "Will Jacks"},
    "PBKS": {"Azmatullah Omarzai", "Lockie Ferguson", "Marco Jansen", "Marcus Stoinis", "Mitch Owen", "Xavier Bartlett"},
    "RCB": {"Jacob Bethell", "Josh Hazlewood", "Nuwan Thushara", "Phil Salt", "Romario Shepherd", "Tim David"},
    "SRH": {"Brydon Carse", "Eshan Malinga", "Heinrich Klaasen", "Kamindu Mendis", "Pat Cummins", "Travis Head"},
}
WICKETKEEPER_HINTS = {
    normalize_name(name)
    for name in [
        "MS Dhoni",
        "Sanju Samson",
        "Urvil Patel",
        "Abhishek Porel",
        "KL Rahul",
        "Jos Buttler",
        "Kumar Kushagra",
        "Anuj Rawat",
        "Rishabh Pant",
        "Nicholas Pooran",
        "Ruturaj Gaikwad",
        "Ishan Kishan",
        "Heinrich Klaasen",
        "Jitesh Sharma",
        "Phil Salt",
        "Prabhsimran Singh",
        "Dhruv Jurel",
        "Donovan Ferreira",
        "Robin Minz",
        "Ryan Rickelton",
    ]
}

MANUAL_STYLE_OVERRIDES = {
    "MS Dhoni": {"bat_style": "RHB", "bowl_style": "", "style_note": "wicketkeeper-finisher with elite game awareness and late-innings boundary access"},
    "Sanju Samson": {"bat_style": "RHB", "bowl_style": ""},
    "Ruturaj Gaikwad": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN", "style_note": "top-order timer who builds tempo through clean down-the-ground strokeplay"},
    "Shivam Dube": {"bat_style": "LHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Noor Ahmad": {"bat_style": "RHB", "bowl_style": "LEFT ARM WRIST SPIN"},
    "Nathan Ellis": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Jamie Overton": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Mukesh Choudhary": {"bat_style": "RHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Syed Khaleel Ahmed": {"bat_style": "RHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Dewald Brevis": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "KL Rahul": {"bat_style": "RHB", "bowl_style": "", "style_note": "top-order anchor with a measured start and strong range once set"},
    "Axar Patel": {"bat_style": "LHB", "bowl_style": "LEFT ARM SLOW ORTHODOX"},
    "Kuldeep Yadav": {"bat_style": "LHB", "bowl_style": "LEFT ARM WRIST SPIN"},
    "Mitchell Starc": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST"},
    "Tristan Stubbs": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "T. Natarajan": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Mukesh Kumar": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Nitish Rana": {"bat_style": "LHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Dushmantha Chameera": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Jos Buttler": {"bat_style": "RHB", "bowl_style": "", "style_note": "explosive top-order hitter who punishes pace and accelerates quickly"},
    "Kagiso Rabada": {"bat_style": "LHB", "bowl_style": "RIGHT ARM FAST"},
    "Mohammad Siraj": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Rashid Khan": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "Shubman Gill": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Sai Sudharsan": {"bat_style": "LHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "Washington Sundar": {"bat_style": "LHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Rahul Tewatia": {"bat_style": "LHB", "bowl_style": "LEFT ARM CHINAMAN"},
    "Prasidh Krishna": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Glenn Phillips": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Sunil Narine": {"bat_style": "LHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Varun Chakaravarthy": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "Harshit Rana": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Ajinkya Rahane": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM", "style_note": "classical top-order batter who relies on timing and placement more than brute power"},
    "Rinku Singh": {"bat_style": "LHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Rovman Powell": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM FAST"},
    "Vaibhav Arora": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Umran Malik": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Nicholas Pooran": {"bat_style": "LHB", "bowl_style": ""},
    "Rishabh Pant": {"bat_style": "LHB", "bowl_style": ""},
    "Mayank Yadav": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Aiden Markram": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Mitchell Marsh": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Md Shami": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Avesh Khan": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Mohsin Khan": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Jasprit Bumrah": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Hardik Pandya": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Rohit Sharma": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN", "style_note": "tempo-setting opener who is strongest when he can dominate pace with pull and pickup shots"},
    "RG Sharma": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN", "style_note": "tempo-setting opener who is strongest when he can dominate pace with pull and pickup shots"},
    "Suryakumar Yadav": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Tilak Verma": {"bat_style": "LHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Trent Boult": {"bat_style": "RHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Deepak Chahar": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Mitchell Santner": {"bat_style": "LHB", "bowl_style": "LEFT ARM SLOW ORTHODOX"},
    "Will Jacks": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Ryan Rickelton": {"bat_style": "LHB", "bowl_style": ""},
    "Shardul Thakur": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Arshdeep Singh": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Marco Jansen": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST"},
    "Lockie Ferguson": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Marcus Stoinis": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Shreyas Iyer": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "Prabhsimran Singh": {"bat_style": "RHB", "bowl_style": ""},
    "Yuzvendra Chahal": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "Harpreet Brar": {"bat_style": "LHB", "bowl_style": "LEFT ARM SLOW ORTHODOX"},
    "Azmatullah Omarzai": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM FAST"},
    "Virat Kohli": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM", "style_note": "high-control top-order batter built on chasing tempo, gap hitting, and low-risk accumulation"},
    "Bhuvneshwar Kumar": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Josh Hazlewood": {"bat_style": "LHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Phil Salt": {"bat_style": "RHB", "bowl_style": ""},
    "Rajat Patidar": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Tim David": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Krunal Pandya": {"bat_style": "LHB", "bowl_style": "LEFT ARM SLOW ORTHODOX"},
    "Nuwan Thushara": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Yash Dayal": {"bat_style": "RHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Yashaswi Jaiswal": {"bat_style": "LHB", "bowl_style": "", "style_note": "left-hand powerplay aggressor who likes to get on top of pace early"},
    "Jofra Archer": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Ravindra Jadeja": {"bat_style": "LHB", "bowl_style": "LEFT ARM SLOW ORTHODOX"},
    "Riyan Parag": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN"},
    "Sam Curran": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST MEDIUM"},
    "Sandeep Sharma": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Shimron Hetmyer": {"bat_style": "LHB", "bowl_style": ""},
    "Dhruv Jurel": {"bat_style": "RHB", "bowl_style": ""},
    "Tushar Deshpande": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Kwena Maphaka": {"bat_style": "LHB", "bowl_style": "LEFT ARM FAST"},
    "Donovan Ferreira": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN"},
    "Vaibhav Suryavanshi": {"bat_style": "LHB", "bowl_style": ""},
    "Travis Head": {"bat_style": "LHB", "bowl_style": "RIGHT ARM OFF SPIN", "style_note": "left-hand attacker who looks to break games open in the powerplay"},
    "Pat Cummins": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Heinrich Klaasen": {"bat_style": "RHB", "bowl_style": ""},
    "Ishan Kishan": {"bat_style": "LHB", "bowl_style": ""},
    "Abhishek Sharma": {"bat_style": "LHB", "bowl_style": "LEFT ARM SLOW ORTHODOX"},
    "Harshal Patel": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST MEDIUM"},
    "Nitish Kumar Reddy": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM FAST"},
    "Brydon Carse": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST"},
    "Kamindu Mendis": {"bat_style": "LHB", "bowl_style": "LEFT ARM ORTHODOX"},
    "Jasprit Bumrah": {"bat_style": "RHB", "bowl_style": "RIGHT ARM FAST", "style_note": "elite pace bowler built on yorkers, seam control, and death-overs problem-solving"},
    "CV Varun": {"bat_style": "RHB", "bowl_style": "RIGHT ARM LEG SPIN", "style_note": "mystery spin operator who squeezes middle overs through pace variation and angle"},
    "Sachin Tendulkar": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM", "style_note": "all-time great top-order batter built on balance, timing, and complete shot range"},
    "SR Tendulkar": {"bat_style": "RHB", "bowl_style": "RIGHT ARM MEDIUM", "style_note": "all-time great top-order batter built on balance, timing, and complete shot range"},
    "Rahul Dravid": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN", "style_note": "classical defensive anchor and Test legend who prized control, judgment, and crease occupation"},
    "R Dravid": {"bat_style": "RHB", "bowl_style": "RIGHT ARM OFF SPIN", "style_note": "classical defensive anchor and Test legend who prized control, judgment, and crease occupation"},
}

FINAL_SQUADS_2026 = {
    "CSK": [
        {"player": "Ruturaj Gaikwad", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "MS Dhoni", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Dewald Brevis", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Ayush Mhatre", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Urvil Patel", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Anshul Kamboj", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Jamie Overton", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Ramakrishna Ghosh", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Shivam Dube", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Khaleel Ahmed", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Noor Ahmad", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Mukesh Choudhary", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Nathan Ellis", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Shreyas Gopal", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Gurjapneet Singh", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Sanju Samson", "acquisition": "Trade", "role": "Wicketkeeper", "price": None},
        {"player": "Akeal Hosein", "acquisition": "Auction", "role": "Bowler", "price": 2.00},
        {"player": "Prashant Veer", "acquisition": "Auction", "role": "All-rounder", "price": 14.20},
        {"player": "Kartik Sharma", "acquisition": "Auction", "role": "Wicketkeeper", "price": 14.20},
        {"player": "Matthew Short", "acquisition": "Auction", "role": "All-rounder", "price": 1.50},
        {"player": "Aman Khan", "acquisition": "Auction", "role": "All-rounder", "price": 0.40},
        {"player": "Sarfaraz Khan", "acquisition": "Auction", "role": "Batter", "price": 0.75},
        {"player": "Rahul Chahar", "acquisition": "Auction", "role": "Bowler", "price": 1.00},
        {"player": "Matt Henry", "acquisition": "Auction", "role": "Bowler", "price": 2.00},
        {"player": "Zak Foulkes", "acquisition": "Auction", "role": "All-rounder", "price": 0.75},
    ],
    "DC": [
        {"player": "KL Rahul", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Karun Nair", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Abhishek Porel", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Tristan Stubbs", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Axar Patel", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Sameer Rizvi", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Ashutosh Sharma", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Vipraj Nigam", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Ajay Mandal", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Tripurana Vijay", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Madhav Tiwari", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Mitchell Starc", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "T. Natarajan", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Mukesh Kumar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Dushmantha Chameera", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Kuldeep Yadav", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Nitish Rana", "acquisition": "Trade", "role": "Batter", "price": None},
        {"player": "Auqib Dar", "acquisition": "Auction", "role": "All-rounder", "price": 8.40},
        {"player": "Ben Duckett", "acquisition": "Auction", "role": "Wicketkeeper", "price": 2.00},
        {"player": "David Miller", "acquisition": "Auction", "role": "Batter", "price": 2.00},
        {"player": "Pathum Nissanka", "acquisition": "Auction", "role": "Batter", "price": 4.00},
        {"player": "Lungi Ngidi", "acquisition": "Auction", "role": "Bowler", "price": 2.00},
        {"player": "Sahil Parakh", "acquisition": "Auction", "role": "Batter", "price": 0.30},
        {"player": "Prithvi Shaw", "acquisition": "Auction", "role": "Batter", "price": 0.75},
        {"player": "Kyle Jamieson", "acquisition": "Auction", "role": "Bowler", "price": 2.00},
    ],
    "GT": [
        {"player": "Shubman Gill", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Sai Sudharsan", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Kumar Kushagra", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Anuj Rawat", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Jos Buttler", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Nishant Sindhu", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Glenn Phillips", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Washington Sundar", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Mohd. Arshad Khan", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Shahrukh Khan", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Rahul Tewatia", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Kagiso Rabada", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Mohammad Siraj", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Prasidh Krishna", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Ishant Sharma", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Gurnoor Singh Brar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Rashid Khan", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Manav Suthar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "R. Sai Kishore", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Jayant Yadav", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Ashok Sharma", "acquisition": "Auction", "role": "Bowler", "price": 0.90},
        {"player": "Jason Holder", "acquisition": "Auction", "role": "All-rounder", "price": 7.00},
        {"player": "Tom Banton", "acquisition": "Auction", "role": "Batter", "price": 2.00},
        {"player": "Luke Wood", "acquisition": "Auction", "role": "Bowler", "price": 0.75},
        {"player": "Prithviraj Yarra", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
    ],
    "KKR": [
        {"player": "Ajinkya Rahane", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Rinku Singh", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Angkrish Raghuvanshi", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Manish Pandey", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Rovman Powell", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Anukul Roy", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Ramandeep Singh", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Vaibhav Arora", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Sunil Narine", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Varun Chakaravarthy", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Harshit Rana", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Umran Malik", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Cameron Green", "acquisition": "Auction", "role": "All-rounder", "price": 25.20},
        {"player": "Matheesha Pathirana", "acquisition": "Auction", "role": "Bowler", "price": 18.00},
        {"player": "Finn Allen", "acquisition": "Auction", "role": "Wicketkeeper", "price": 2.00},
        {"player": "Tejasvi Singh", "acquisition": "Auction", "role": "Wicketkeeper", "price": 3.00},
        {"player": "Prashant Solanki", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Kartik Tyagi", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Rahul Tripathi", "acquisition": "Auction", "role": "Batter", "price": 0.75},
        {"player": "Tim Seifert", "acquisition": "Auction", "role": "Wicketkeeper", "price": 1.50},
        {"player": "Sarthak Ranjan", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Daksh Kamra", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Akash Deep", "acquisition": "Auction", "role": "Bowler", "price": 1.00},
        {"player": "Rachin Ravindra", "acquisition": "Auction", "role": "All-rounder", "price": 2.00},
        {"player": "Blessing Muzarabani", "acquisition": "Replacement", "role": "Bowler", "price": None},
    ],
    "LSG": [
        {"player": "Rishabh Pant", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Ayush Badoni", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Abdul Samad", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Aiden Markram", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Himmat Singh", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Matthew Breetzke", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Nicholas Pooran", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Mitchell Marsh", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Shahbaz Ahmed", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Arshin Kulkarni", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Mayank Yadav", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Avesh Khan", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Mohsin Khan", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Manimaran Siddharth", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Digvesh Rathi", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Prince Yadav", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Akash Singh", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Arjun Tendulkar", "acquisition": "Trade", "role": "Bowler", "price": None},
        {"player": "Md Shami", "acquisition": "Trade", "role": "Bowler", "price": None},
        {"player": "Anrich Nortje", "acquisition": "Auction", "role": "Bowler", "price": 2.00},
        {"player": "Wanindu Hasaranga", "acquisition": "Auction", "role": "All-rounder", "price": 2.00},
        {"player": "Mukul Choudhary", "acquisition": "Auction", "role": "Wicketkeeper", "price": 2.60},
        {"player": "Naman Tiwari", "acquisition": "Auction", "role": "All-rounder", "price": 1.00},
        {"player": "Akshat Raghuwanshi", "acquisition": "Auction", "role": "Batter", "price": 2.20},
        {"player": "Josh Inglis", "acquisition": "Auction", "role": "Batter", "price": 8.60},
    ],
    "MI": [
        {"player": "Rohit Sharma", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Suryakumar Yadav", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Robin Minz", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Ryan Rickelton", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Tilak Verma", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Hardik Pandya", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Naman Dhir", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Mitchell Santner", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Will Jacks", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Corbin Bosch", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Raj Angad Bawa", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Trent Boult", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Jasprit Bumrah", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Deepak Chahar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Ashwani Kumar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Raghu Sharma", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Allah Ghazanfar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Mayank Markande", "acquisition": "Trade", "role": "Bowler", "price": None},
        {"player": "Shardul Thakur", "acquisition": "Trade", "role": "All-rounder", "price": None},
        {"player": "Sherfane Rutherford", "acquisition": "Trade", "role": "Batter", "price": None},
        {"player": "Quinton De Kock", "acquisition": "Auction", "role": "Wicketkeeper", "price": 1.00},
        {"player": "Atharva Ankolekar", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Mohammad Izhar", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Danish Malewar", "acquisition": "Auction", "role": "Batter", "price": 0.30},
        {"player": "Mayank Rawat", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
    ],
    "PBKS": [
        {"player": "Shreyas Iyer", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Nehal Wadhera", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Vishnu Vinod", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Harnoor Pannu", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Pyla Avinash", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Prabhsimran Singh", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Shashank Singh", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Marcus Stoinis", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Harpreet Brar", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Marco Jansen", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Azmatullah Omarzai", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Priyansh Arya", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Musheer Khan", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Suryansh Shedge", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Mitch Owen", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Arshdeep Singh", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Yuzvendra Chahal", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Vyshak Vijaykumar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Yash Thakur", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Xavier Bartlett", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Lockie Ferguson", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Cooper Connolly", "acquisition": "Auction", "role": "All-rounder", "price": 3.00},
        {"player": "Ben Dwarshuis", "acquisition": "Auction", "role": "All-rounder", "price": 4.40},
        {"player": "Vishal Nishad", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Pravin Dubey", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
    ],
    "RR": [
        {"player": "Shubham Dubey", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Vaibhav Suryavanshi", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Lhuan-Dre Pretorious", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Shimron Hetmyer", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Yashaswi Jaiswal", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Dhruv Jurel", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Riyan Parag", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Yudhvir Charak", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Jofra Archer", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Tushar Deshpande", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Sandeep Sharma", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Kwena Maphaka", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Nandre Burger", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Ravindra Jadeja", "acquisition": "Trade", "role": "All-rounder", "price": None},
        {"player": "Sam Curran", "acquisition": "Trade", "role": "All-rounder", "price": None},
        {"player": "Donovan Ferreira", "acquisition": "Trade", "role": "Wicketkeeper", "price": None},
        {"player": "Ravi Bishnoi", "acquisition": "Auction", "role": "Bowler", "price": 7.20},
        {"player": "Sushant Mishra", "acquisition": "Auction", "role": "Bowler", "price": 0.90},
        {"player": "Vignesh Puthur", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Yash Raj Punja", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Ravi Singh", "acquisition": "Auction", "role": "Wicketkeeper", "price": 0.95},
        {"player": "Brijesh Sharma", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Aman Rao", "acquisition": "Auction", "role": "Batter", "price": 0.30},
        {"player": "Adam Milne", "acquisition": "Auction", "role": "Bowler", "price": 2.40},
        {"player": "Kuldeep Sen", "acquisition": "Auction", "role": "Bowler", "price": 0.75},
    ],
    "RCB": [
        {"player": "Rajat Patidar", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Virat Kohli", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Tim David", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Devdutt Padikkal", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Phil Salt", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Jitesh Sharma", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Krunal Pandya", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Jacob Bethell", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Romario Shepherd", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Swapnil Singh", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Josh Hazlewood", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Bhuvneshwar Kumar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Rasikh Dar", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Yash Dayal", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Suyash Sharma", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Nuwan Thushara", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Abhinandan Singh", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Venkatesh Iyer", "acquisition": "Auction", "role": "All-rounder", "price": 7.00},
        {"player": "Jacob Duffy", "acquisition": "Auction", "role": "Bowler", "price": 2.00},
        {"player": "Mangesh Yadav", "acquisition": "Auction", "role": "All-rounder", "price": 5.20},
        {"player": "Satvik Deswal", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Jordan Cox", "acquisition": "Auction", "role": "Batter", "price": 0.75},
        {"player": "Kanishk Chouhan", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Vihaan Malhotra", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Vicky Ostwal", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
    ],
    "SRH": [
        {"player": "Travis Head", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Abhishek Sharma", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Aniket Verma", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Smaran Ravichandaran", "acquisition": "Retained", "role": "Batter", "price": None},
        {"player": "Ishan Kishan", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Heinrich Klaasen", "acquisition": "Retained", "role": "Wicketkeeper", "price": None},
        {"player": "Nitish Kumar Reddy", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Harsh Dubey", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Kamindu Mendis", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Harshal Patel", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Brydon Carse", "acquisition": "Retained", "role": "All-rounder", "price": None},
        {"player": "Pat Cummins", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Jaydev Unadkat", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Eshan Malinga", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Zeeshan Ansari", "acquisition": "Retained", "role": "Bowler", "price": None},
        {"player": "Shivang Kumar", "acquisition": "Auction", "role": "All-rounder", "price": 0.30},
        {"player": "Salil Arora", "acquisition": "Auction", "role": "Wicketkeeper", "price": 1.50},
        {"player": "Krains Fuletra", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Praful Hinge", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Amit Kumar", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Onkar Tarmale", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Sakib Hussain", "acquisition": "Auction", "role": "Bowler", "price": 0.30},
        {"player": "Liam Livingstone", "acquisition": "Auction", "role": "All-rounder", "price": 13.00},
        {"player": "Shivam Mavi", "acquisition": "Auction", "role": "Bowler", "price": 0.75},
        {"player": "Jack Edwards", "acquisition": "Auction", "role": "All-rounder", "price": 3.00},
    ],
}

MATCH_SCHEDULE_2026 = [
    {"date": "2026-03-28", "home": "RCB", "away": "SRH", "start": "7:30 PM", "venue": "Bengaluru"},
    {"date": "2026-03-29", "home": "MI", "away": "KKR", "start": "7:30 PM", "venue": "Mumbai"},
    {"date": "2026-03-30", "home": "RR", "away": "CSK", "start": "7:30 PM", "venue": "Guwahati"},
    {"date": "2026-03-31", "home": "PBKS", "away": "GT", "start": "7:30 PM", "venue": "Mullanpur"},
    {"date": "2026-04-01", "home": "LSG", "away": "DC", "start": "7:30 PM", "venue": "Lucknow"},
    {"date": "2026-04-02", "home": "KKR", "away": "SRH", "start": "7:30 PM", "venue": "Kolkata"},
    {"date": "2026-04-03", "home": "CSK", "away": "PBKS", "start": "7:30 PM", "venue": "Chennai"},
    {"date": "2026-04-04", "home": "DC", "away": "MI", "start": "3:30 PM", "venue": "Delhi"},
    {"date": "2026-04-04", "home": "GT", "away": "RR", "start": "7:30 PM", "venue": "Ahmedabad"},
    {"date": "2026-04-05", "home": "SRH", "away": "LSG", "start": "3:30 PM", "venue": "Hyderabad"},
    {"date": "2026-04-05", "home": "RCB", "away": "CSK", "start": "7:30 PM", "venue": "Bengaluru"},
    {"date": "2026-04-06", "home": "KKR", "away": "PBKS", "start": "7:30 PM", "venue": "Kolkata"},
    {"date": "2026-04-07", "home": "RR", "away": "MI", "start": "7:30 PM", "venue": "Guwahati"},
    {"date": "2026-04-08", "home": "DC", "away": "GT", "start": "7:30 PM", "venue": "Delhi"},
    {"date": "2026-04-09", "home": "KKR", "away": "LSG", "start": "7:30 PM", "venue": "Kolkata"},
    {"date": "2026-04-10", "home": "RR", "away": "RCB", "start": "7:30 PM", "venue": "Guwahati"},
    {"date": "2026-04-11", "home": "PBKS", "away": "SRH", "start": "3:30 PM", "venue": "Mullanpur"},
    {"date": "2026-04-11", "home": "CSK", "away": "DC", "start": "7:30 PM", "venue": "Chennai"},
    {"date": "2026-04-12", "home": "LSG", "away": "GT", "start": "3:30 PM", "venue": "Lucknow"},
    {"date": "2026-04-12", "home": "MI", "away": "RCB", "start": "7:30 PM", "venue": "Mumbai"},
]

CITY_ALIASES = {
    "bengaluru": "bengaluru",
    "bangalore": "bengaluru",
    "mumbai": "mumbai",
    "guwahati": "guwahati",
    "mullanpur": "mullanpur",
    "lucknow": "lucknow",
    "kolkata": "kolkata",
    "chennai": "chennai",
    "delhi": "delhi",
    "ahmedabad": "ahmedabad",
    "hyderabad": "hyderabad",
}


def compact_initials_key(name: str) -> str:
    norm = normalize_name(name)
    if not norm:
        return ""
    parts = norm.split()
    if len(parts) == 1:
        return parts[0]
    return f"{''.join(part[0] for part in parts[:-1])} {parts[-1]}"


def build_player_style_lookup(player_meta: pd.DataFrame) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for _, row in player_meta.iterrows():
        raw_name = str(row.get("player_name", "")).strip()
        canonical_name = canonical_player_name(raw_name)
        bat_style = str(row.get("bat_style", "") or "").strip()
        bowl_style = str(row.get("bowl_style", "") or "").strip()
        style_note = str(row.get("style_note", "") or "").strip()
        keys = {
            normalize_name(raw_name),
            normalize_name(canonical_name),
            first_initial_key(raw_name),
            first_initial_key(canonical_name),
            compact_initials_key(raw_name),
            compact_initials_key(canonical_name),
        }
        for key in keys:
            if not key:
                continue
            entry = registry.setdefault(key, {"bat_style": "", "bowl_style": "", "style_note": ""})
            if bat_style and not entry["bat_style"]:
                entry["bat_style"] = bat_style
            if bowl_style and not entry["bowl_style"]:
                entry["bowl_style"] = bowl_style
            if style_note and not entry["style_note"]:
                entry["style_note"] = style_note
    return registry


def build_dashboard_player_style_lookup() -> dict[str, dict[str, str]]:
    auction_pool = add_player_valuation_columns(load_auction_pool("2026"), season="2026")
    player_meta = auction_pool.sort_values(["player_name"]).drop_duplicates("player_name").copy()
    player_meta["style_note"] = ""
    override_meta = pd.DataFrame(
        [
            {
                "player_name": name,
                "bat_style": values.get("bat_style", ""),
                "bowl_style": values.get("bowl_style", ""),
                "style_note": values.get("style_note", ""),
            }
            for name, values in MANUAL_STYLE_OVERRIDES.items()
        ]
    )
    player_meta = pd.concat(
        [player_meta[["player_name", "bat_style", "bowl_style", "style_note"]], override_meta],
        ignore_index=True,
    )
    return build_player_style_lookup(player_meta)


def compute_batter_style_profile(
    player: str,
    summary_row: pd.Series,
    phase_profile: dict[str, dict[str, float]],
    pace_spin_rows: pd.DataFrame,
    pressure_rows: pd.DataFrame,
    player_style_lookup: dict[str, dict[str, str]],
) -> dict[str, str]:
    hand = player_style_lookup.get(normalize_name(player), {}).get("bat_style", "")
    phase_scores = {phase: float(phase_profile.get(phase, {}).get("impact_pct", 0.0)) for phase in PHASE_ORDER}
    top_phase = max(phase_scores, key=phase_scores.get) if phase_scores else "middle"
    top_phase_score = phase_scores.get(top_phase, 0.0)
    if top_phase_score < 55:
        phase_identity = "balanced phase profile"
    elif top_phase == "powerplay":
        phase_identity = "powerplay aggressor"
    elif top_phase == "middle":
        phase_identity = "middle-overs stabilizer"
    else:
        phase_identity = "death overs finisher"

    pace_sr = (
        safe_float(pace_spin_rows.loc[pace_spin_rows["bowl_family"] == "Pace", "strike_rate"].mean())
        if not pace_spin_rows.empty
        else 0.0
    )
    spin_sr = (
        safe_float(pace_spin_rows.loc[pace_spin_rows["bowl_family"] == "Spin", "strike_rate"].mean())
        if not pace_spin_rows.empty
        else 0.0
    )
    if pace_sr and spin_sr:
        if pace_sr - spin_sr >= 12:
            pace_spin_bias = "stronger against pace"
        elif spin_sr - pace_sr >= 12:
            pace_spin_bias = "stronger against spin"
        else:
            pace_spin_bias = "balanced against pace and spin"
    else:
        pace_spin_bias = "limited pace-spin split sample"

    if summary_row["strike_rate"] >= 140:
        scoring_style = "high-tempo boundary hitter"
    elif summary_row["strike_rate"] <= 118 and summary_row["dismissal_rate"] <= 0.05:
        scoring_style = "accumulator"
    else:
        scoring_style = "mixed scorer"

    high_pressure_sr = safe_float(
        pressure_rows.loc[pressure_rows["pressure_state"] == "High Pressure", "strike_rate"].mean()
    )
    standard_sr = safe_float(pressure_rows.loc[pressure_rows["pressure_state"] == "Standard", "strike_rate"].mean())
    if high_pressure_sr and standard_sr:
        if high_pressure_sr - standard_sr >= 8:
            pressure_trait = "lifts scoring under pressure"
        elif standard_sr - high_pressure_sr >= 8:
            pressure_trait = "less explosive under pressure"
        else:
            pressure_trait = "stable across pressure states"
    else:
        pressure_trait = "limited pressure sample"

    return {
        "handedness": hand or "Unknown",
        "phase_identity": phase_identity,
        "scoring_style": scoring_style,
        "pace_spin_bias": pace_spin_bias,
        "pressure_trait": pressure_trait,
        "style_note": player_style_lookup.get(normalize_name(player), {}).get("style_note", ""),
    }


def compute_bowler_style_profile(
    player: str,
    summary_row: pd.Series,
    phase_profile: dict[str, dict[str, float]],
    hand_rows: pd.DataFrame,
    pressure_rows: pd.DataFrame,
    player_style_lookup: dict[str, dict[str, str]],
) -> dict[str, str]:
    raw_style = player_style_lookup.get(normalize_name(player), {}).get("bowl_style", "")
    family = bowl_family_from_style(raw_style) or "Unknown"
    phase_scores = {phase: float(phase_profile.get(phase, {}).get("impact_pct", 0.0)) for phase in PHASE_ORDER}
    top_phase = max(phase_scores, key=phase_scores.get) if phase_scores else "middle"
    top_phase_score = phase_scores.get(top_phase, 0.0)
    if top_phase_score < 55:
        phase_identity = "utility overs option"
    elif top_phase == "powerplay":
        phase_identity = "new-ball specialist"
    elif top_phase == "middle":
        phase_identity = "middle-overs controller"
    else:
        phase_identity = "death overs specialist"

    if summary_row["economy"] <= 7.4 and summary_row["wicket_rate"] <= 0.045:
        attack_profile = "control bowler"
    elif summary_row["wicket_rate"] >= 0.055:
        attack_profile = "wicket-taking threat"
    else:
        attack_profile = "balanced operator"

    lhb_econ = safe_float(hand_rows.loc[hand_rows["batter_hand"] == "LHB", "economy"].mean())
    rhb_econ = safe_float(hand_rows.loc[hand_rows["batter_hand"] == "RHB", "economy"].mean())
    if lhb_econ and rhb_econ:
        if rhb_econ - lhb_econ >= 0.75:
            handedness_bias = "better against left-hand batters"
        elif lhb_econ - rhb_econ >= 0.75:
            handedness_bias = "better against right-hand batters"
        else:
            handedness_bias = "neutral by batter handedness"
    else:
        handedness_bias = "limited handedness split sample"

    high_pressure_econ = safe_float(
        pressure_rows.loc[pressure_rows["pressure_state"] == "High Pressure", "economy"].mean()
    )
    standard_econ = safe_float(pressure_rows.loc[pressure_rows["pressure_state"] == "Standard", "economy"].mean())
    if high_pressure_econ and standard_econ:
        if standard_econ - high_pressure_econ >= 0.6:
            pressure_trait = "sharpens under pressure"
        elif high_pressure_econ - standard_econ >= 0.6:
            pressure_trait = "more hittable under pressure"
        else:
            pressure_trait = "steady across pressure states"
    else:
        pressure_trait = "limited pressure sample"

    return {
        "bowling_family": family,
        "bowling_style": raw_style or "Unknown style",
        "phase_identity": phase_identity,
        "attack_profile": attack_profile,
        "handedness_bias": handedness_bias,
        "pressure_trait": pressure_trait,
        "style_note": player_style_lookup.get(normalize_name(player), {}).get("style_note", ""),
    }


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
    auction_pool = add_player_valuation_columns(load_auction_pool("2026"), season="2026")
    league_summary_df = pd.read_csv(DATA_DIR / "league_auction_mc_summary_2026.csv")
    if "mc_top_target" in league_summary_df.columns:
        league_summary_df["mc_top_target"] = league_summary_df["mc_top_target"].fillna("").map(canonical_player_name).replace({"": None})
    league_summary = league_summary_df.to_dict("records")
    league_events = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events.csv")
    league_events_mc = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events_mc.csv")
    for col in ["player_name", "winner", "runner_up"]:
        if col in league_events.columns:
            league_events[col] = league_events[col].fillna("").map(canonical_player_name).replace({"": None})
        if col in league_events_mc.columns:
            league_events_mc[col] = league_events_mc[col].fillna("").map(canonical_player_name).replace({"": None})
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

    mc_runs = max(int(league_events_mc["run_id"].nunique()), 1)
    market_stats = (
        league_events_mc.groupby(["player_name", "role_bucket"])
        .agg(
            expected_price=("final_price", "mean"),
            price_std=("final_price", "std"),
            times_sold=("run_id", "nunique"),
        )
        .reset_index()
    )
    market_stats["purchase_share"] = market_stats["times_sold"] / mc_runs

    role_market_df = auction_pool.copy()
    role_market_df["player_name"] = role_market_df["player_name"].map(canonical_player_name)
    role_market_df = role_market_df.merge(market_stats, on=["player_name", "role_bucket"], how="left")
    role_market_df["expected_price"] = role_market_df["expected_price"].fillna(role_market_df["reserve_price"])
    role_market_df["price_std"] = role_market_df["price_std"].fillna(0.0)
    role_market_df["purchase_share"] = role_market_df["purchase_share"].fillna(0.0)
    role_market_df["value_surplus"] = role_market_df["base_ceiling"] - role_market_df["expected_price"]
    role_market_df["quality_gap_from_top"] = role_market_df.groupby("role_bucket")["quality_score"].transform("max") - role_market_df["quality_score"]
    role_market_df = role_market_df.sort_values(["role_bucket", "quality_score", "value_surplus"], ascending=[True, False, False])

    role_market = {
        role: frame[
            [
                "player_name",
                "role_bucket",
                "reserve_price",
                "expected_price",
                "price_std",
                "quality_score",
                "base_ceiling",
                "value_surplus",
                "purchase_share",
                "quality_gap_from_top",
                "is_overseas",
            ]
        ]
        .head(20)
        .round({"reserve_price": 2, "expected_price": 2, "price_std": 2, "quality_score": 4, "base_ceiling": 2, "value_surplus": 2, "purchase_share": 3, "quality_gap_from_top": 4})
        .to_dict("records")
        for role, frame in role_market_df.groupby("role_bucket")
    }

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
        "role_market": {
            "roles": sorted(role_market.keys()),
            "options_by_role": role_market,
            "methodology": (
                "Role-market boards use league-wide Monte Carlo auction events to estimate expected clearing prices by player, "
                "then compare those prices with each player's model ceiling to measure value surplus and the quality drop-off within a role."
            ),
        },
}


def infer_team_player_role(
    player: str,
    batter_balls: dict[str, float],
    bowler_balls: dict[str, float],
    batter_phase_identity: dict[str, str],
    player_style_lookup: dict[str, dict[str, str]],
) -> str:
    norm = normalize_name(player)
    bat_balls = float(batter_balls.get(player, 0.0))
    bowl_balls = float(bowler_balls.get(player, 0.0))
    bowl_style = player_style_lookup.get(norm, {}).get("bowl_style", "")
    bowl_family = bowl_family_from_style(bowl_style)
    if norm in WICKETKEEPER_HINTS:
        return "wicketkeeper"
    if bat_balls >= 90 and bowl_balls >= 90:
        return "all_rounder"
    if bowl_balls >= 120 and bat_balls < 80:
        if bowl_family == "Spin":
            return "spinner"
        if bowl_family == "Pace":
            return "pacer"
        return "bowler"
    phase_identity = batter_phase_identity.get(player, "")
    if phase_identity == "powerplay aggressor":
        return "opener"
    if phase_identity == "death overs finisher":
        return "finisher"
    if bat_balls >= 90:
        return "middle_order"
    if bowl_family == "Spin":
        return "spinner"
    if bowl_family == "Pace":
        return "pacer"
    return "utility"


def build_team_payload() -> dict:
    configs = resolve_team_configs("2026")
    states = build_team_states(configs)
    player_style_lookup = build_dashboard_player_style_lookup()
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv", usecols=["batter", "bowler", "legal_ball"])

    batter_balls = (
        ball.groupby("batter")["legal_ball"].sum().rename(index=canonical_player_name).groupby(level=0).sum().to_dict()
    )
    bowler_balls = (
        ball.groupby("bowler")["legal_ball"].sum().rename(index=canonical_player_name).groupby(level=0).sum().to_dict()
    )

    batter_phase_identity: dict[str, str] = {}
    batter_phase_scores: dict[str, dict[str, float]] = {}
    for phase, path in PHASE_FILES["batting"].items():
        phase_df = pd.read_csv(path)
        phase_df["impact_pct"] = phase_df["impact_score"].rank(pct=True) * 100.0
        for _, row in phase_df.iterrows():
            batter_phase_scores.setdefault(canonical_player_name(str(row["batter"])), {})[phase] = float(row["impact_pct"])
    for player, scores in batter_phase_scores.items():
        if not scores:
            continue
        top_phase = max(scores, key=scores.get)
        if scores[top_phase] < 55:
            batter_phase_identity[player] = "balanced phase profile"
        elif top_phase == "powerplay":
            batter_phase_identity[player] = "powerplay aggressor"
        elif top_phase == "death":
            batter_phase_identity[player] = "death overs finisher"
        else:
            batter_phase_identity[player] = "middle-overs stabilizer"

    role_display = {
        "wicketkeeper": "Wicketkeeper",
        "opener": "Opener",
        "middle_order": "Middle Order",
        "finisher": "Finisher",
        "all_rounder": "All-Rounder",
        "spinner": "Spin",
        "pacer": "Pace",
        "bowler": "Bowler",
        "utility": "Utility",
    }
    skeleton_order = ["wicketkeeper", "opener", "opener", "middle_order", "middle_order", "finisher", "all_rounder", "spinner", "pacer", "pacer", "utility"]
    slot_fallbacks = {
        "wicketkeeper": ["middle_order", "finisher"],
        "opener": ["middle_order"],
        "middle_order": ["finisher", "all_rounder", "opener"],
        "finisher": ["all_rounder", "middle_order"],
        "all_rounder": ["middle_order", "spinner", "pacer"],
        "spinner": ["all_rounder", "utility", "bowler"],
        "pacer": ["bowler", "utility", "all_rounder"],
        "utility": ["all_rounder", "bowler", "middle_order", "finisher", "spinner", "pacer"],
    }

    auction_payload = build_auction_payload()
    teams = []
    for code, config in configs.items():
        state = states[code]
        retained_players = [canonical_player_name(player) for player in config["retained_players"]]
        retained_overseas = RETAINED_OVERSEAS_PLAYERS.get(code, set())
        locked_players = LOCKED_XI_PLAYERS.get(code, {})
        retained_roles = []
        for player in retained_players:
            retained_roles.append(
                {
                    "player": player,
                    "role": infer_team_player_role(player, batter_balls, bowler_balls, batter_phase_identity, player_style_lookup),
                    "is_overseas": player in retained_overseas,
                    "locked": player in locked_players,
                    "lock_reason": locked_players.get(player),
                }
            )

        remaining = retained_roles.copy()
        xi_slots = [{"slot_key": slot, "slot": role_display[slot], "player": "Open", "filled": False, "locked": False, "is_overseas": False, "lock_reason": None} for slot in skeleton_order]
        overseas_in_xi = 0

        def role_priority(entry: dict[str, object], target_role: str) -> tuple[float, float, float]:
            score = 0.0
            if entry["role"] == target_role:
                score += 4.0
            elif entry["role"] in slot_fallbacks.get(target_role, []):
                score += 2.0
            if entry.get("locked"):
                score += 5.0
            if not entry.get("is_overseas"):
                score += 0.8
            player_name = str(entry["player"])
            score += float(batter_balls.get(player_name, 0.0) + bowler_balls.get(player_name, 0.0)) / 500.0
            return (score, float(batter_balls.get(player_name, 0.0)), float(bowler_balls.get(player_name, 0.0)))

        def choose_slot_index(entry: dict[str, object]) -> int | None:
            preferred_roles = [entry["role"], *slot_fallbacks.get(str(entry["role"]), [])]
            for preferred_role in preferred_roles:
                for idx, slot in enumerate(xi_slots):
                    if not slot["filled"] and slot["slot_key"] == preferred_role:
                        return idx
            for idx, slot in enumerate(xi_slots):
                if not slot["filled"]:
                    return idx
            return None

        def place_entry(entry: dict[str, object]) -> None:
            nonlocal overseas_in_xi
            idx = choose_slot_index(entry)
            if idx is None:
                return
            xi_slots[idx] = {
                "slot_key": xi_slots[idx]["slot_key"],
                "slot": xi_slots[idx]["slot"],
                "player": entry["player"],
                "filled": True,
                "locked": bool(entry.get("locked")),
                "is_overseas": bool(entry.get("is_overseas")),
                "lock_reason": entry.get("lock_reason"),
            }
            if entry.get("is_overseas"):
                overseas_in_xi += 1
            remaining.remove(entry)

        locked_entries = [entry for entry in remaining if entry.get("locked")]
        for entry in locked_entries:
            place_entry(entry)

        for idx, slot in enumerate(xi_slots):
            if slot["filled"]:
                continue
            candidates = [
                entry
                for entry in remaining
                if (
                    entry["role"] == slot["slot_key"]
                    or entry["role"] in slot_fallbacks.get(slot["slot_key"], [])
                )
                and (not entry.get("is_overseas") or overseas_in_xi < PLAYING_XI_OVERSEAS_LIMIT)
            ]
            if not candidates:
                candidates = [
                    entry
                    for entry in remaining
                    if not entry.get("is_overseas") or overseas_in_xi < PLAYING_XI_OVERSEAS_LIMIT
                ]
            if not candidates:
                continue
            best = sorted(candidates, key=lambda entry: role_priority(entry, slot["slot_key"]), reverse=True)[0]
            place_entry(best)

        role_counts: dict[str, int] = {}
        for entry in retained_roles:
            role_counts[entry["role"]] = role_counts.get(entry["role"], 0) + 1

        recommended_fills = auction_payload["teams"][code]["top_targets"][:4]
        overseas_pressure = round(
            (max(0, state.overseas_limit - state.overseas_retained) / max(1, state.squad_size - state.retained)) * 100,
            1,
        )
        role_gaps = [
            {"role": role.replace("_", " "), "weight": weight}
            for role, weight in sorted(config.get("role_needs", {}).items(), key=lambda item: item[1], reverse=True)
        ]

        teams.append(
            {
                "code": code,
                "name": config["name"],
                "purse": config["purse"],
                "spent": config["spent"],
                "retained": config["retained"],
                "overseas_retained": config["overseas_retained"],
                "retained_players": retained_players,
                "role_needs": config.get("role_needs", {}),
                "role_caps": config.get("role_caps", {}),
                "auction_power": state.auction_power,
                "aggression": state.aggression,
                "open_slots": max(0, state.squad_size - state.retained),
                "overseas_slots_left": max(0, state.overseas_limit - state.overseas_retained),
                "xi_skeleton": xi_slots,
                "retained_role_counts": [
                    {"role": role_display.get(role, role.title()), "count": count}
                    for role, count in sorted(role_counts.items(), key=lambda item: (-item[1], item[0]))
                ],
                "bench_depth": [
                    {"player": entry["player"], "role": role_display.get(entry["role"], entry["role"].title())}
                    for entry in remaining
                ],
                "recommended_fills": recommended_fills,
                "role_gaps": role_gaps[:5],
                "overseas_pressure_pct": overseas_pressure,
                "xi_overseas_count": overseas_in_xi,
                "xi_overseas_limit": PLAYING_XI_OVERSEAS_LIMIT,
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
    ball["season_year"] = pd.to_datetime(ball["date"]).dt.year
    player_style_lookup = build_dashboard_player_style_lookup()
    auction_pool = add_player_valuation_columns(load_auction_pool("2026"), season="2026")
    league_events_mc = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events_mc.csv")
    ball["batter_norm"] = ball["batter"].map(normalize_name)
    ball["bowler_norm"] = ball["bowler"].map(normalize_name)
    ball["batter_hand"] = ball["batter_norm"].map(lambda key: player_style_lookup.get(key, {}).get("bat_style", "")).replace({"": None})
    ball["bowler_style"] = ball["bowler_norm"].map(lambda key: player_style_lookup.get(key, {}).get("bowl_style", "")).replace({"": None})
    ball["bowl_family"] = ball["bowler_style"].map(bowl_family_from_style)
    ball["pressure_state"] = (
        (ball["balls_remaining"] <= 30) | (ball["innings_wickets_cum"] >= 5)
    ).map({True: "High Pressure", False: "Standard"})

    batter_base = (
        ball.groupby("batter")
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", "sum"),
            last_year=("date", lambda values: int(pd.to_datetime(values).dt.year.max())),
            matches=("match_id", "nunique"),
            run_value=("run_value", "sum"),
        )
        .reset_index()
        .rename(columns={"batter": "player"})
    )
    batter_base["strike_rate"] = (batter_base["runs"] / batter_base["balls"].clip(lower=1)) * 100
    batter_base["dismissal_rate"] = batter_base["dismissals"] / batter_base["balls"].clip(lower=1)
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
    bowler_base["wicket_rate"] = bowler_base["wickets"] / bowler_base["balls"].clip(lower=1)
    bowler_base["wins_added"] = -bowler_base["run_value"] / 15.0

    market_stats = (
        league_events_mc.assign(player_name=league_events_mc["player_name"].map(canonical_player_name))
        .groupby("player_name")
        .agg(expected_price=("final_price", "mean"), purchase_share=("run_id", "nunique"))
        .reset_index()
    )
    total_runs = max(int(league_events_mc["run_id"].nunique()), 1)
    market_stats["purchase_share"] = market_stats["purchase_share"] / total_runs
    market_lookup_df = auction_pool.copy()
    market_lookup_df["player_name"] = market_lookup_df["player_name"].map(canonical_player_name)
    market_lookup_df = market_lookup_df.merge(market_stats, on="player_name", how="left")
    market_lookup = (
        market_lookup_df.sort_values(["quality_score", "base_ceiling"], ascending=False)
        .drop_duplicates("player_name")
        .set_index("player_name")[
            ["role_bucket", "is_overseas", "quality_score", "base_ceiling", "expected_price", "purchase_share"]
        ]
        .to_dict("index")
    )

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

    batter_yearly = (
        ball.groupby(["batter", "season_year"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            matches=("match_id", "nunique"),
            run_value=("run_value", "sum"),
        )
        .reset_index()
    )
    batter_yearly["strike_rate"] = (batter_yearly["runs"] / batter_yearly["balls"].clip(lower=1)) * 100.0
    batter_yearly["wins_added"] = batter_yearly["run_value"] / 15.0

    bowler_yearly = (
        ball.groupby(["bowler", "season_year"])
        .agg(
            runs=("runs_total", "sum"),
            balls=("legal_ball", "sum"),
            wickets=("wicket", "sum"),
            matches=("match_id", "nunique"),
            run_value=("run_value", "sum"),
        )
        .reset_index()
    )
    bowler_yearly["economy"] = bowler_yearly["runs"] / (bowler_yearly["balls"].clip(lower=1) / 6.0)
    bowler_yearly["wins_added"] = -bowler_yearly["run_value"] / 15.0

    batter_phase_yearly = (
        ball.groupby(["batter", "season_year", "phase"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"))
        .reset_index()
    )
    batter_phase_yearly["strike_rate"] = (batter_phase_yearly["runs"] / batter_phase_yearly["balls"].clip(lower=1)) * 100.0
    batter_phase_yearly["phase_impact"] = batter_phase_yearly["strike_rate"] * batter_phase_yearly["balls"]

    bowler_phase_yearly = (
        ball.groupby(["bowler", "season_year", "phase"])
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"))
        .reset_index()
    )
    phase_league_econ = (
        bowler_phase_yearly.groupby(["season_year", "phase"])
        .agg(runs=("runs", "sum"), balls=("balls", "sum"))
        .reset_index()
    )
    phase_league_econ["league_econ"] = phase_league_econ["runs"] / (phase_league_econ["balls"].clip(lower=1) / 6.0)
    bowler_phase_yearly = bowler_phase_yearly.merge(
        phase_league_econ[["season_year", "phase", "league_econ"]], on=["season_year", "phase"], how="left"
    )
    bowler_phase_yearly["economy"] = bowler_phase_yearly["runs"] / (bowler_phase_yearly["balls"].clip(lower=1) / 6.0)
    bowler_phase_yearly["phase_impact"] = (
        (bowler_phase_yearly["league_econ"] - bowler_phase_yearly["economy"]) * bowler_phase_yearly["balls"]
        + 25.0 * bowler_phase_yearly["wickets"]
    )

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

    batter_phase_profiles: dict[str, dict[str, dict[str, float]]] = {}
    bowler_phase_profiles: dict[str, dict[str, dict[str, float]]] = {}
    for phase in PHASE_ORDER:
        bat_frame = batter_phase_frames[phase].copy()
        bowl_frame = bowler_phase_frames[phase].copy()
        bat_frame["impact_pct"] = bat_frame["impact_score"].rank(pct=True) * 100.0
        bowl_frame["impact_pct"] = bowl_frame["impact_score"].rank(pct=True) * 100.0
        for _, phase_row in bat_frame.iterrows():
            batter_phase_profiles.setdefault(canonical_player_name(str(phase_row["batter"])), {})[phase] = {
                "impact_pct": round(float(phase_row["impact_pct"]), 2)
            }
        for _, phase_row in bowl_frame.iterrows():
            bowler_phase_profiles.setdefault(canonical_player_name(str(phase_row["bowler"])), {})[phase] = {
                "impact_pct": round(float(phase_row["impact_pct"]), 2)
            }

    def trend_signal(trend_rows: list[dict]) -> str:
        if len(trend_rows) < 2:
            return "limited sample"
        values = [float(row["wins_added"]) for row in trend_rows]
        recent = sum(values[-2:]) / min(2, len(values))
        previous_window = values[:-2] if len(values) > 2 else values[:1]
        previous = sum(previous_window) / max(len(previous_window), 1)
        delta = recent - previous
        if delta >= 2.0:
            return "rising strongly"
        if delta >= 0.75:
            return "trending up"
        if delta <= -2.0:
            return "declining sharply"
        if delta <= -0.75:
            return "cooling off"
        return "stable"

    batter_profiles = {}
    for _, row in batter_base.sort_values("runs", ascending=False).iterrows():
        player = row["player"]
        display_player = canonical_player_name(str(player))
        yearly_rows = batter_yearly[batter_yearly["batter"] == player].sort_values("season_year")
        yearly_phase_rows = batter_phase_yearly[batter_phase_yearly["batter"] == player]
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
            "market": (
                None
                if display_player not in market_lookup
                else {
                    "role_bucket": market_lookup[display_player]["role_bucket"],
                    "is_overseas": bool(market_lookup[display_player]["is_overseas"]),
                    "quality_score": round(float(market_lookup[display_player]["quality_score"]), 4),
                    "base_ceiling": round(float(market_lookup[display_player]["base_ceiling"]), 2),
                    "expected_price": None
                    if pd.isna(market_lookup[display_player].get("expected_price"))
                    else round(float(market_lookup[display_player]["expected_price"]), 2),
                    "purchase_share": round(float(market_lookup[display_player].get("purchase_share") or 0.0), 3),
                }
            ),
        }
        batter_profiles[display_player]["style"] = compute_batter_style_profile(
            display_player,
            row,
            batter_phase_profiles.get(display_player, {}),
            batter_vs_style[batter_vs_style["batter"] == player],
            pressure_batting[pressure_batting["batter"] == player],
            player_style_lookup,
        )
        yearly_trend = []
        for _, yearly_row in yearly_rows.iterrows():
            season_phase = yearly_phase_rows[yearly_phase_rows["season_year"] == yearly_row["season_year"]]
            best_phase = (
                season_phase.sort_values("phase_impact", ascending=False).iloc[0]["phase"]
                if not season_phase.empty
                else "middle"
            )
            yearly_trend.append(
                {
                    "year": int(yearly_row["season_year"]),
                    "impact_score": round(float(yearly_row["run_value"]), 2),
                    "wins_added": round(float(yearly_row["wins_added"]), 2),
                    "matches": int(yearly_row["matches"]),
                    "best_phase": str(best_phase),
                }
            )
        batter_profiles[display_player]["yearly_trend"] = yearly_trend
        batter_profiles[display_player]["trend_signal"] = trend_signal(yearly_trend)

    bowler_profiles = {}
    for _, row in bowler_base.sort_values("wickets", ascending=False).iterrows():
        player = row["player"]
        display_player = canonical_player_name(str(player))
        yearly_rows = bowler_yearly[bowler_yearly["bowler"] == player].sort_values("season_year")
        yearly_phase_rows = bowler_phase_yearly[bowler_phase_yearly["bowler"] == player]
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
            "market": (
                None
                if display_player not in market_lookup
                else {
                    "role_bucket": market_lookup[display_player]["role_bucket"],
                    "is_overseas": bool(market_lookup[display_player]["is_overseas"]),
                    "quality_score": round(float(market_lookup[display_player]["quality_score"]), 4),
                    "base_ceiling": round(float(market_lookup[display_player]["base_ceiling"]), 2),
                    "expected_price": None
                    if pd.isna(market_lookup[display_player].get("expected_price"))
                    else round(float(market_lookup[display_player]["expected_price"]), 2),
                    "purchase_share": round(float(market_lookup[display_player].get("purchase_share") or 0.0), 3),
                }
            ),
        }
        bowler_profiles[display_player]["style"] = compute_bowler_style_profile(
            display_player,
            row,
            bowler_phase_profiles.get(display_player, {}),
            bowler_vs_hand[bowler_vs_hand["bowler"] == player],
            pressure_bowling[pressure_bowling["bowler"] == player],
            player_style_lookup,
        )
        yearly_trend = []
        for _, yearly_row in yearly_rows.iterrows():
            season_phase = yearly_phase_rows[yearly_phase_rows["season_year"] == yearly_row["season_year"]]
            best_phase = (
                season_phase.sort_values("phase_impact", ascending=False).iloc[0]["phase"]
                if not season_phase.empty
                else "middle"
            )
            yearly_trend.append(
                {
                    "year": int(yearly_row["season_year"]),
                    "impact_score": round(float(yearly_row["wins_added"]), 2),
                    "wins_added": round(float(yearly_row["wins_added"]), 2),
                    "matches": int(yearly_row["matches"]),
                    "best_phase": str(best_phase),
                }
            )
        bowler_profiles[display_player]["yearly_trend"] = yearly_trend
        bowler_profiles[display_player]["trend_signal"] = trend_signal(yearly_trend)

    def similarity_reason(primary_style: dict[str, str], other_style: dict[str, str], keys: list[str], fallback: str) -> str:
        shared = []
        labels = {
            "handedness": "same handedness",
            "phase_identity": "same phase role",
            "scoring_style": "similar scoring style",
            "pace_spin_bias": "similar pace-spin profile",
            "bowling_family": "same bowling family",
            "attack_profile": "similar attack profile",
            "handedness_bias": "similar handedness matchup profile",
            "pressure_trait": "similar pressure response",
        }
        for key in keys:
            if primary_style.get(key) and primary_style.get(key) == other_style.get(key):
                shared.append(labels.get(key, key.replace("_", " ")))
        return ", ".join(shared[:2]) if shared else fallback

    def batter_similarity(profile: dict, other: dict) -> tuple[float, str]:
        radar_diff = sum(
            abs(float(a["value"]) - float(b["value"]))
            for a, b in zip(profile["radar"], other["radar"], strict=False)
        ) / max(len(profile["radar"]), 1)
        style = profile["style"]
        other_style = other["style"]
        score = 92 - 1.1 * radar_diff
        if style.get("handedness") == other_style.get("handedness") and style.get("handedness") != "Unknown":
            score += 2
        if style.get("phase_identity") == other_style.get("phase_identity"):
            score += 3
        if style.get("scoring_style") == other_style.get("scoring_style"):
            score += 2
        if style.get("pace_spin_bias") == other_style.get("pace_spin_bias"):
            score += 2
        if style.get("pressure_trait") == other_style.get("pressure_trait"):
            score += 1
        score = max(0.0, min(98.0, score))
        reason = similarity_reason(
            style,
            other_style,
            ["phase_identity", "scoring_style", "pace_spin_bias", "pressure_trait", "handedness"],
            "closest overall batting profile by phase and scoring pattern",
        )
        return round(score, 1), reason

    def bowler_similarity(profile: dict, other: dict) -> tuple[float, str]:
        radar_diff = sum(
            abs(float(a["value"]) - float(b["value"]))
            for a, b in zip(profile["radar"], other["radar"], strict=False)
        ) / max(len(profile["radar"]), 1)
        style = profile["style"]
        other_style = other["style"]
        score = 92 - 1.1 * radar_diff
        if style.get("bowling_family") == other_style.get("bowling_family") and style.get("bowling_family") != "Unknown":
            score += 3
        if style.get("phase_identity") == other_style.get("phase_identity"):
            score += 3
        if style.get("attack_profile") == other_style.get("attack_profile"):
            score += 2
        if style.get("handedness_bias") == other_style.get("handedness_bias"):
            score += 1
        if style.get("pressure_trait") == other_style.get("pressure_trait"):
            score += 1
        score = max(0.0, min(98.0, score))
        reason = similarity_reason(
            style,
            other_style,
            ["phase_identity", "attack_profile", "bowling_family", "handedness_bias", "pressure_trait"],
            "closest overall bowling profile by phase, control, and wicket shape",
        )
        return round(score, 1), reason

    for profile in batter_profiles.values():
        comps = []
        for other in batter_profiles.values():
            if other["player"] == profile["player"]:
                continue
            score, reason = batter_similarity(profile, other)
            comps.append(
                {
                    "player": other["player"],
                    "similarity_score": score,
                    "reason": reason,
                    "impact_score": other["summary"]["impact_score"],
                    "wins_added": other["summary"]["wins_added"],
                    "phase_identity": other["style"]["phase_identity"],
                }
            )
        profile["comps"] = sorted(comps, key=lambda item: (-item["similarity_score"], -item["impact_score"]))[:12]

    for profile in bowler_profiles.values():
        comps = []
        for other in bowler_profiles.values():
            if other["player"] == profile["player"]:
                continue
            score, reason = bowler_similarity(profile, other)
            comps.append(
                {
                    "player": other["player"],
                    "similarity_score": score,
                    "reason": reason,
                    "impact_score": other["summary"]["impact_score"],
                    "wins_added": other["summary"]["wins_added"],
                    "phase_identity": other["style"]["phase_identity"],
                }
            )
        profile["comps"] = sorted(comps, key=lambda item: (-item["similarity_score"], -item["impact_score"]))[:12]

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
            "player_comps": {
                "title": "Player Comps Construction",
                "text": (
                    "Player comps combine three layers: phase radar shape, derived style labels, and pressure-trait alignment. "
                    "Similarity scores therefore reflect not just aggregate output, but whether two players score or control innings in similar windows."
                ),
            },
            "trajectory": {
                "title": "Trajectory And Form View",
                "text": (
                    "Season trends track year-by-year wins-added and phase-leading impact proxies. The trend signal compares recent seasons with the player's earlier baseline "
                    "to flag whether the profile is rising, stable, or cooling off."
                ),
            },
        },
    }


def build_scenario_payload() -> dict:
    team_configs = resolve_team_configs("2026")
    states = build_team_states(team_configs)
    auction_pool = add_player_valuation_columns(load_auction_pool("2026"), season="2026")
    league_events = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events.csv")
    league_events_mc = pd.read_csv(DATA_DIR / "league_auction_simulation_2026_events_mc.csv")
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv", usecols=["batter", "bowler", "date"])
    batter_last_year = (
        ball.groupby("batter")["date"]
        .max()
        .rename(index=canonical_player_name)
        .groupby(level=0)
        .max()
        .map(lambda value: int(pd.to_datetime(value).year))
        .to_dict()
    )
    bowler_last_year = (
        ball.groupby("bowler")["date"]
        .max()
        .rename(index=canonical_player_name)
        .groupby(level=0)
        .max()
        .map(lambda value: int(pd.to_datetime(value).year))
        .to_dict()
    )
    player_last_year = {**batter_last_year}
    for player, year in bowler_last_year.items():
        player_last_year[player] = max(year, player_last_year.get(player, 0))

    event_lookup = (
        league_events.assign(player_name=league_events["player_name"].map(canonical_player_name)).drop_duplicates("player_name")
        .set_index("player_name")[["winner", "final_price", "runner_up", "set_no"]]
        .to_dict("index")
    )
    market_lookup = (
        league_events_mc.assign(player_name=league_events_mc["player_name"].map(canonical_player_name))
        .groupby("player_name")
        .agg(expected_price=("final_price", "mean"), purchase_share=("run_id", "nunique"))
        .assign(purchase_share=lambda frame: frame["purchase_share"] / max(int(league_events_mc["run_id"].nunique()), 1))
        .to_dict("index")
    )

    players = []
    for _, row in auction_pool.iterrows():
        player_name = canonical_player_name(str(row["player_name"]))
        rep = event_lookup.get(player_name, {})
        market = market_lookup.get(player_name, {})
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
                "expected_price": round(float(market.get("expected_price", row["reserve_price"])), 2),
                "purchase_share": round(float(market.get("purchase_share", 0.0)), 3),
                "runner_up": rep.get("runner_up"),
                "is_overseas": bool(row["is_overseas"]),
                "bowl_family": bowl_family_from_style(row.get("bowl_style")),
                "bat_hand": str(row.get("bat_style") or "").upper() or None,
                "age": safe_int(row.get("Age")),
                "ipl_matches": safe_int(row.get("ipl_matches")),
                "t20_caps": safe_int(row.get("t20_caps")),
                "capped_flag": int(safe_float(row.get("capped_flag"))),
                "prev_ipl_2025": int(safe_float(row.get("prev_ipl_2025"))),
                "active_flag": bool(
                    player_last_year.get(player_name, 0) >= ACTIVE_CUTOFF_YEAR or safe_float(row.get("prev_ipl_2025")) > 0
                ),
                "last_year": safe_int(player_last_year.get(player_name, 0)),
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
    )
    override_meta = pd.DataFrame(
        [
            {
                "player_name": name,
                "bat_style": values.get("bat_style", ""),
                "bowl_style": values.get("bowl_style", ""),
                "style_note": values.get("style_note", ""),
            }
            for name, values in MANUAL_STYLE_OVERRIDES.items()
        ]
    )
    player_meta["style_note"] = ""
    player_meta = pd.concat([player_meta[["player_name", "bat_style", "bowl_style", "style_note"]], override_meta], ignore_index=True)
    player_style_lookup = build_player_style_lookup(player_meta)

    ball = ball.copy()
    ball["batter_norm"] = ball["batter"].map(normalize_name)
    ball["bowler_norm"] = ball["bowler"].map(normalize_name)
    ball["batter_hand"] = ball["batter_norm"].map(lambda key: player_style_lookup.get(key, {}).get("bat_style", "")).replace({"": None})
    ball["bowler_style"] = ball["bowler_norm"].map(lambda key: player_style_lookup.get(key, {}).get("bowl_style", "")).replace({"": None})
    ball["bowl_family"] = ball["bowler_style"].map(bowl_family_from_style)
    ball["pressure_state"] = (
        (ball["balls_remaining"] <= 30) | (ball["innings_wickets_cum"] >= 5)
    ).map({True: "High Pressure", False: "Standard"})

    batter_overall = (
        ball.groupby("batter")
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), dismissals=("wicket", "sum"))
        .reset_index()
    )
    batter_overall["strike_rate"] = (batter_overall["runs"] / batter_overall["balls"].clip(lower=1)) * 100.0
    batter_overall["dismissal_rate"] = batter_overall["dismissals"] / batter_overall["balls"].clip(lower=1)

    bowler_overall = (
        ball.groupby("bowler")
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"))
        .reset_index()
    )
    bowler_overall["economy"] = bowler_overall["runs"] / (bowler_overall["balls"].clip(lower=1) / 6.0)
    bowler_overall["wicket_rate"] = bowler_overall["wickets"] / bowler_overall["balls"].clip(lower=1)

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

    batter_context = batter_overall.copy()
    batter_context["batter"] = batter_context["batter"].map(canonical_player_name)
    batter_style_profiles = {}
    for _, row in batter_context.iterrows():
        player = row["batter"]
        phase_profile = batter_phase_profiles.get(player, {})
        pace_spin_rows = batter_vs_style[batter_vs_style["batter"] == player]
        pressure_rows = pressure_batting[pressure_batting["batter"] == player]
        hand = player_style_lookup.get(normalize_name(player), {}).get("bat_style", "")
        phase_scores = {phase: float(phase_profile.get(phase, {}).get("impact_pct", 0.0)) for phase in PHASE_ORDER}
        top_phase = max(phase_scores, key=phase_scores.get) if phase_scores else "middle"
        top_phase_score = phase_scores.get(top_phase, 0.0)
        if top_phase_score < 55:
            phase_identity = "balanced phase profile"
        elif top_phase == "powerplay":
            phase_identity = "powerplay aggressor"
        elif top_phase == "middle":
            phase_identity = "middle-overs stabilizer"
        else:
            phase_identity = "death overs finisher"

        pace_sr = safe_float(pace_spin_rows.loc[pace_spin_rows["bowl_family"] == "Pace", "strike_rate"].mean()) if not pace_spin_rows.empty else 0.0
        spin_sr = safe_float(pace_spin_rows.loc[pace_spin_rows["bowl_family"] == "Spin", "strike_rate"].mean()) if not pace_spin_rows.empty else 0.0
        if pace_sr and spin_sr:
            if pace_sr - spin_sr >= 12:
                pace_spin_bias = "stronger against pace"
            elif spin_sr - pace_sr >= 12:
                pace_spin_bias = "stronger against spin"
            else:
                pace_spin_bias = "balanced against pace and spin"
        else:
            pace_spin_bias = "limited pace-spin split sample"

        if row["strike_rate"] >= 140:
            scoring_style = "high-tempo boundary hitter"
        elif row["strike_rate"] <= 118 and row["dismissal_rate"] <= 0.05:
            scoring_style = "accumulator"
        else:
            scoring_style = "mixed scorer"

        high_pressure_sr = safe_float(pressure_rows.loc[pressure_rows["pressure_state"] == "High Pressure", "strike_rate"].mean())
        standard_sr = safe_float(pressure_rows.loc[pressure_rows["pressure_state"] == "Standard", "strike_rate"].mean())
        if high_pressure_sr and standard_sr:
            if high_pressure_sr - standard_sr >= 8:
                pressure_trait = "lifts scoring under pressure"
            elif standard_sr - high_pressure_sr >= 8:
                pressure_trait = "less explosive under pressure"
            else:
                pressure_trait = "stable across pressure states"
        else:
            pressure_trait = "limited pressure sample"

        batter_style_profiles[player] = {
            "handedness": hand or "Unknown",
            "phase_identity": phase_identity,
            "scoring_style": scoring_style,
            "pace_spin_bias": pace_spin_bias,
            "pressure_trait": pressure_trait,
            "style_note": player_style_lookup.get(normalize_name(player), {}).get("style_note", ""),
        }

    bowler_context = bowler_overall.copy()
    bowler_context["bowler"] = bowler_context["bowler"].map(canonical_player_name)
    bowler_style_profiles = {}
    for _, row in bowler_context.iterrows():
        player = row["bowler"]
        phase_profile = bowler_phase_profiles.get(player, {})
        hand_rows = bowler_vs_hand[bowler_vs_hand["bowler"] == player]
        pressure_rows = pressure_bowling[pressure_bowling["bowler"] == player]
        raw_style = player_style_lookup.get(normalize_name(player), {}).get("bowl_style", "")
        family = bowl_family_from_style(raw_style) or "Unknown"
        phase_scores = {phase: float(phase_profile.get(phase, {}).get("impact_pct", 0.0)) for phase in PHASE_ORDER}
        top_phase = max(phase_scores, key=phase_scores.get) if phase_scores else "middle"
        top_phase_score = phase_scores.get(top_phase, 0.0)
        if top_phase_score < 55:
            phase_identity = "utility overs option"
        elif top_phase == "powerplay":
            phase_identity = "new-ball specialist"
        elif top_phase == "middle":
            phase_identity = "middle-overs controller"
        else:
            phase_identity = "death overs specialist"

        if row["economy"] <= 7.4 and row["wicket_rate"] <= 0.045:
            bowling_style = "control bowler"
        elif row["wicket_rate"] >= 0.055:
            bowling_style = "wicket-taking threat"
        else:
            bowling_style = "balanced operator"

        lhb_econ = safe_float(hand_rows.loc[hand_rows["batter_hand"] == "LHB", "economy"].mean())
        rhb_econ = safe_float(hand_rows.loc[hand_rows["batter_hand"] == "RHB", "economy"].mean())
        if lhb_econ and rhb_econ:
            if rhb_econ - lhb_econ >= 0.75:
                handedness_bias = "better against left-hand batters"
            elif lhb_econ - rhb_econ >= 0.75:
                handedness_bias = "better against right-hand batters"
            else:
                handedness_bias = "neutral by batter handedness"
        else:
            handedness_bias = "limited handedness split sample"

        high_pressure_econ = safe_float(pressure_rows.loc[pressure_rows["pressure_state"] == "High Pressure", "economy"].mean())
        standard_econ = safe_float(pressure_rows.loc[pressure_rows["pressure_state"] == "Standard", "economy"].mean())
        if high_pressure_econ and standard_econ:
            if standard_econ - high_pressure_econ >= 0.6:
                pressure_trait = "sharpens under pressure"
            elif high_pressure_econ - standard_econ >= 0.6:
                pressure_trait = "more hittable under pressure"
            else:
                pressure_trait = "steady across pressure states"
        else:
            pressure_trait = "limited pressure sample"

        bowler_style_profiles[player] = {
            "bowling_family": family,
            "bowling_style": raw_style or "Unknown style",
            "phase_identity": phase_identity,
            "attack_profile": bowling_style,
            "handedness_bias": handedness_bias,
            "pressure_trait": pressure_trait,
            "style_note": player_style_lookup.get(normalize_name(player), {}).get("style_note", ""),
        }

    bowler_options = sorted(
        {
            canonical_player_name(str(name))
            for name in ball["bowler"].dropna().astype(str).unique().tolist()
        }
    )

    return {
        "batter_options": sorted(batter_vs_style["batter"].unique().tolist()),
        "bowler_options": bowler_options,
        "batter_vs_style": batter_vs_style.to_dict("records"),
        "bowler_vs_hand": bowler_vs_hand.to_dict("records"),
        "pressure_batting": pressure_batting.to_dict("records"),
        "pressure_bowling": pressure_bowling.to_dict("records"),
        "head_to_head_total": head_to_head_total.to_dict("records"),
        "head_to_head_phase": head_to_head_phase.to_dict("records"),
        "batter_phase_profiles": batter_phase_profiles,
        "bowler_phase_profiles": bowler_phase_profiles,
        "batter_style_profiles": batter_style_profiles,
        "bowler_style_profiles": bowler_style_profiles,
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


def build_match_planning_payload(players_payload: dict) -> dict:
    ball = pd.read_csv(DATA_DIR / "ipl_ball_by_ball.csv", parse_dates=["date"])
    ball["season_year"] = ball["date"].dt.year
    ball["batter_name"] = ball["batter"].map(canonical_player_name)
    ball["bowler_name"] = ball["bowler"].map(canonical_player_name)
    ball["pressure_state"] = (
        (ball["balls_remaining"] <= 30) | (ball["innings_wickets_cum"] >= 5)
    ).map({True: "High Pressure", False: "Standard"})
    ball["location_key"] = (
        ball["city"]
        .fillna(ball["venue"])
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda value: CITY_ALIASES.get(value, value))
    )

    active_batters = {
        name: profile
        for name, profile in players_payload["batter_profiles"].items()
        if int(profile["summary"].get("last_year", 0)) >= ACTIVE_CUTOFF_YEAR
    }
    active_bowlers = {
        name: profile
        for name, profile in players_payload["bowler_profiles"].items()
        if int(profile["summary"].get("last_year", 0)) >= ACTIVE_CUTOFF_YEAR
    }

    venue_phase = (
        ball.groupby(["location_key", "phase"])
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"))
        .reset_index()
    )
    venue_phase["run_rate"] = venue_phase["runs"] / (venue_phase["balls"].clip(lower=1) / 6.0)
    venue_phase["wicket_rate"] = venue_phase["wickets"] / venue_phase["balls"].clip(lower=1)

    innings_totals = (
        ball.groupby(["match_id", "innings", "location_key"])
        .agg(total=("innings_runs_cum", "max"))
        .reset_index()
    )
    venue_innings = innings_totals.groupby("location_key").agg(avg_total=("total", "mean"), innings_count=("total", "size")).reset_index()

    venue_batting = (
        ball[ball["batter_name"].isin(active_batters)]
        .groupby(["location_key", "batter_name"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), matches=("match_id", "nunique"))
        .reset_index()
    )
    venue_batting = venue_batting[venue_batting["balls"] >= 20].copy()
    venue_batting["strike_rate"] = venue_batting["runs"] / venue_batting["balls"].clip(lower=1) * 100.0
    venue_batting["impact_proxy"] = venue_batting["runs"] + 0.6 * venue_batting["balls"]

    venue_bowling = (
        ball[ball["bowler_name"].isin(active_bowlers)]
        .groupby(["location_key", "bowler_name"])
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"), matches=("match_id", "nunique"))
        .reset_index()
    )
    venue_bowling = venue_bowling[venue_bowling["balls"] >= 18].copy()
    venue_bowling["economy"] = venue_bowling["runs"] / (venue_bowling["balls"].clip(lower=1) / 6.0)
    venue_bowling["impact_proxy"] = 25.0 * venue_bowling["wickets"] - venue_bowling["runs"] / 6.0

    venue_pressure_batting = (
        ball[(ball["batter_name"].isin(active_batters)) & (ball["pressure_state"] == "High Pressure")]
        .groupby(["location_key", "batter_name"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), dismissals=("wicket", "sum"), matches=("match_id", "nunique"))
        .reset_index()
    )
    venue_pressure_batting = venue_pressure_batting[venue_pressure_batting["balls"] >= 12].copy()
    venue_pressure_batting["strike_rate"] = (
        venue_pressure_batting["runs"] / venue_pressure_batting["balls"].clip(lower=1) * 100.0
    )
    venue_pressure_batting["dismissal_rate"] = (
        venue_pressure_batting["dismissals"] / venue_pressure_batting["balls"].clip(lower=1)
    )
    venue_pressure_batting["pressure_score"] = (
        venue_pressure_batting["runs"]
        + 0.35 * venue_pressure_batting["balls"]
        - 45.0 * venue_pressure_batting["dismissal_rate"]
    )

    venue_pressure_bowling = (
        ball[(ball["bowler_name"].isin(active_bowlers)) & (ball["pressure_state"] == "High Pressure")]
        .groupby(["location_key", "bowler_name"])
        .agg(runs=("runs_total", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"), matches=("match_id", "nunique"))
        .reset_index()
    )
    venue_pressure_bowling = venue_pressure_bowling[venue_pressure_bowling["balls"] >= 12].copy()
    venue_pressure_bowling["economy"] = (
        venue_pressure_bowling["runs"] / (venue_pressure_bowling["balls"].clip(lower=1) / 6.0)
    )
    venue_pressure_bowling["wicket_rate"] = (
        venue_pressure_bowling["wickets"] / venue_pressure_bowling["balls"].clip(lower=1)
    )
    venue_pressure_bowling["pressure_score"] = (
        28.0 * venue_pressure_bowling["wickets"] - venue_pressure_bowling["economy"] * 3.5
    )

    venue_profiles = {}
    for venue in sorted({item["venue"] for item in MATCH_SCHEDULE_2026}):
        venue_key = CITY_ALIASES.get(venue.strip().lower(), venue.strip().lower())
        phase_rows = venue_phase[venue_phase["location_key"] == venue_key]
        innings_row = venue_innings[venue_innings["location_key"] == venue_key]
        top_bat = (
            venue_batting[venue_batting["location_key"] == venue_key]
            .sort_values(["impact_proxy", "strike_rate"], ascending=[False, False])
            .head(5)[["batter_name", "runs", "strike_rate", "matches"]]
            .round({"strike_rate": 1})
            .rename(columns={"batter_name": "player"})
            .to_dict("records")
        )
        top_bowl = (
            venue_bowling[venue_bowling["location_key"] == venue_key]
            .sort_values(["impact_proxy", "wickets"], ascending=[False, False])
            .head(5)[["bowler_name", "economy", "wickets", "matches"]]
            .round({"economy": 2})
            .rename(columns={"bowler_name": "player"})
            .to_dict("records")
        )
        pressure_bat = (
            venue_pressure_batting[venue_pressure_batting["location_key"] == venue_key]
            .sort_values(["pressure_score", "strike_rate"], ascending=[False, False])
            .head(5)[["batter_name", "runs", "strike_rate", "matches"]]
            .round({"strike_rate": 1})
            .rename(columns={"batter_name": "player"})
            .to_dict("records")
        )
        pressure_bowl = (
            venue_pressure_bowling[venue_pressure_bowling["location_key"] == venue_key]
            .sort_values(["pressure_score", "wickets"], ascending=[False, False])
            .head(5)[["bowler_name", "wickets", "economy", "matches"]]
            .round({"economy": 2})
            .rename(columns={"bowler_name": "player"})
            .to_dict("records")
        )
        venue_profiles[venue] = {
            "avg_total": round(float(innings_row["avg_total"].iloc[0]), 1) if not innings_row.empty else None,
            "innings_count": int(innings_row["innings_count"].iloc[0]) if not innings_row.empty else 0,
            "phase_conditions": phase_rows[["phase", "run_rate", "wicket_rate"]].round({"run_rate": 2, "wicket_rate": 3}).to_dict("records"),
            "top_batters": top_bat,
            "top_bowlers": top_bowl,
            "pressure_batters": pressure_bat,
            "pressure_bowlers": pressure_bowl,
        }

    team_profiles = {}

    def active_team_profiles(team_code: str) -> dict:
        squad = FINAL_SQUADS_2026[team_code]
        active_players = []
        no_sample = []
        for entry in squad:
            player = canonical_player_name(entry["player"])
            batter = active_batters.get(player)
            bowler = active_bowlers.get(player)
            if batter or bowler:
                active_players.append(
                    {
                        "player": player,
                        "role": entry["role"],
                        "acquisition": entry["acquisition"],
                        "price": entry["price"],
                        "batter": batter,
                        "bowler": bowler,
                    }
                )
            else:
                no_sample.append(player)
        return {"active_players": active_players, "no_sample": no_sample}

    for team_code in FINAL_SQUADS_2026:
        team_profiles[team_code] = active_team_profiles(team_code)

    duel_total = (
        ball.groupby(["batter_name", "bowler_name"])
        .agg(runs=("runs_batter", "sum"), balls=("legal_ball", "sum"), wickets=("wicket", "sum"))
        .reset_index()
    )
    duel_total["strike_rate"] = duel_total["runs"] / duel_total["balls"].clip(lower=1) * 100.0
    duel_lookup = {
        (row["batter_name"], row["bowler_name"]): {
            "runs": int(row["runs"]),
            "balls": int(row["balls"]),
            "wickets": int(row["wickets"]),
            "strike_rate": float(row["strike_rate"]),
        }
        for _, row in duel_total.iterrows()
        if row["balls"] >= 3
    }

    def team_phase_snapshot(team_code: str) -> dict[str, float]:
        active_players = team_profiles[team_code]["active_players"]
        batting_scores = {phase: [] for phase in PHASE_ORDER}
        bowling_scores = {phase: [] for phase in PHASE_ORDER}
        wins_added = []
        for row in active_players:
            if row["batter"]:
                wins_added.append(float(row["batter"]["summary"].get("wins_added", 0.0)))
                for phase in PHASE_ORDER:
                    batting_scores[phase].append(float(row["batter"]["phase_details"].get(phase, {}).get("impact_score", 0.0)))
            if row["bowler"]:
                wins_added.append(float(row["bowler"]["summary"].get("wins_added", 0.0)))
                for phase in PHASE_ORDER:
                    bowling_scores[phase].append(float(row["bowler"]["phase_details"].get(phase, {}).get("impact_score", 0.0)))
        return {
            "bat_powerplay": round(sum(sorted(batting_scores["powerplay"], reverse=True)[:3]), 2),
            "bat_middle": round(sum(sorted(batting_scores["middle"], reverse=True)[:3]), 2),
            "bat_death": round(sum(sorted(batting_scores["death"], reverse=True)[:3]), 2),
            "bowl_powerplay": round(sum(sorted(bowling_scores["powerplay"], reverse=True)[:3]), 2),
            "bowl_middle": round(sum(sorted(bowling_scores["middle"], reverse=True)[:3]), 2),
            "bowl_death": round(sum(sorted(bowling_scores["death"], reverse=True)[:3]), 2),
            "wins_added_total": round(sum(sorted(wins_added, reverse=True)[:8]), 2),
            "active_count": len(active_players),
            "no_sample_count": len(team_profiles[team_code]["no_sample"]),
        }

    snapshots = {team_code: team_phase_snapshot(team_code) for team_code in FINAL_SQUADS_2026}

    def radar_lookup(profile: dict) -> dict[str, float]:
        return {row["axis"]: float(row["value"]) for row in profile.get("radar", [])}

    def phase_score(profile: dict, phase: str) -> float:
        axis_map = {
            "powerplay": "PP Impact",
            "middle": "Middle Impact",
            "death": "Death Impact",
        }
        radar = radar_lookup(profile)
        return float(radar.get(axis_map[phase], 0.0))

    def top_phase(profile: dict, kind: str) -> str:
        phase_values = {phase: phase_score(profile, phase) for phase in PHASE_ORDER}
        if kind == "bowling":
            return max(phase_values, key=phase_values.get)
        return max(phase_values, key=phase_values.get)

    def venue_bat_bonus(player: str, venue: str) -> float:
        venue_key = CITY_ALIASES.get(venue.strip().lower(), venue.strip().lower())
        row = venue_batting[(venue_batting["location_key"] == venue_key) & (venue_batting["batter_name"] == player)]
        if row.empty:
            return 0.0
        return float(row["strike_rate"].iloc[0] - venue_batting[venue_batting["location_key"] == venue_key]["strike_rate"].mean()) / 12.0

    def venue_bowl_bonus(player: str, venue: str) -> float:
        venue_key = CITY_ALIASES.get(venue.strip().lower(), venue.strip().lower())
        row = venue_bowling[(venue_bowling["location_key"] == venue_key) & (venue_bowling["bowler_name"] == player)]
        if row.empty:
            return 0.0
        venue_mean = venue_bowling[venue_bowling["location_key"] == venue_key]["economy"].mean()
        return float(venue_mean - row["economy"].iloc[0]) / 0.8

    def batting_role_weight(role: str) -> float:
        return {
            "Batter": 1.0,
            "Wicketkeeper": 0.95,
            "All-rounder": 0.68,
            "Bowler": 0.2,
        }.get(role, 0.7)

    def bowling_role_weight(role: str) -> float:
        return {
            "Bowler": 1.0,
            "All-rounder": 0.78,
            "Batter": 0.18,
            "Wicketkeeper": 0.15,
        }.get(role, 0.7)

    def acquisition_weight(acquisition: str) -> float:
        return {
            "Retained": 1.0,
            "Trade": 0.96,
            "Auction": 0.88,
            "Replacement": 0.8,
        }.get(acquisition, 0.9)

    def matchup_edge(batter_profile: dict, bowler_profile: dict, batter_name: str, bowler_name: str) -> float:
        batter_best = top_phase(batter_profile, "batting")
        bowler_best = top_phase(bowler_profile, "bowling")
        shared_phase = batter_best if batter_best == bowler_best else batter_best
        edge = phase_score(batter_profile, shared_phase) / 10.0 - phase_score(bowler_profile, shared_phase) / 10.0
        duel = duel_lookup.get((batter_name, bowler_name))
        if duel:
            reliability = min(duel["balls"], 18) / 18.0
            edge += reliability * ((duel["strike_rate"] - 120.0) / 18.0)
            edge -= reliability * duel["wickets"] * 1.4
        return edge

    def rank_team_players(team_code: str, kind: str, venue: str, opponent_code: str, limit: int = 4) -> list[dict]:
        active_players = team_profiles[team_code]["active_players"]
        opponent_active = team_profiles[opponent_code]["active_players"]
        opponent_bowlers = [row for row in opponent_active if row["bowler"]]
        opponent_batters = [row for row in opponent_active if row["batter"]]
        rows = []
        for row in active_players:
            profile = row["batter"] if kind == "batting" else row["bowler"]
            if not profile:
                continue
            summary = profile["summary"]
            radar = radar_lookup(profile)
            if kind == "batting":
                matchup_component = sum(
                    matchup_edge(profile, opp["bowler"], row["player"], opp["player"])
                    for opp in opponent_bowlers[:4]
                ) / max(min(len(opponent_bowlers), 4), 1)
                venue_component = venue_bat_bonus(row["player"], venue)
                base_component = (
                    0.28 * radar.get("PP Impact", 0.0)
                    + 0.24 * radar.get("Middle Impact", 0.0)
                    + 0.18 * radar.get("Death Impact", 0.0)
                    + 0.16 * radar.get("Volume", 0.0)
                    + 0.14 * radar.get("Wins Added", 0.0)
                )
                role_component = batting_role_weight(row["role"]) * acquisition_weight(row["acquisition"])
            else:
                matchup_component = sum(
                    -matchup_edge(opp["batter"], profile, opp["player"], row["player"])
                    for opp in opponent_batters[:4]
                ) / max(min(len(opponent_batters), 4), 1)
                venue_component = venue_bowl_bonus(row["player"], venue)
                base_component = (
                    0.24 * radar.get("PP Impact", 0.0)
                    + 0.28 * radar.get("Middle Impact", 0.0)
                    + 0.22 * radar.get("Death Impact", 0.0)
                    + 0.12 * radar.get("Control", 0.0)
                    + 0.14 * radar.get("Wickets", 0.0)
                )
                role_component = bowling_role_weight(row["role"]) * acquisition_weight(row["acquisition"])
            game_score = role_component * (base_component + 8.0 * matchup_component + 5.0 * venue_component)
            rows.append(
                {
                    "player": row["player"],
                    "role": row["role"],
                    "impact_score": round(float(summary.get("impact_score", 0.0)), 2),
                    "wins_added": round(float(summary.get("wins_added", 0.0)), 2),
                    "style_note": profile["style"].get("style_note", ""),
                    "phase_identity": profile["style"].get("phase_identity", ""),
                    "game_score": round(game_score, 2),
                    "venue_boost": round(venue_component, 2),
                    "matchup_score": round(matchup_component, 2),
                    "role_weight": round(role_component, 2),
                }
            )
        rows.sort(key=lambda item: (item["game_score"], item["impact_score"], item["wins_added"]), reverse=True)
        return rows[:limit]

    def rank_team_core(team_code: str, kind: str, limit: int = 3) -> list[dict]:
        active_players = team_profiles[team_code]["active_players"]
        rows = []
        for row in active_players:
            profile = row["batter"] if kind == "batting" else row["bowler"]
            if not profile:
                continue
            radar = radar_lookup(profile)
            summary = profile["summary"]
            if kind == "batting":
                core_score = batting_role_weight(row["role"]) * acquisition_weight(row["acquisition"]) * (
                    0.3 * radar.get("PP Impact", 0.0)
                    + 0.26 * radar.get("Middle Impact", 0.0)
                    + 0.16 * radar.get("Death Impact", 0.0)
                    + 0.14 * radar.get("Volume", 0.0)
                    + 0.14 * radar.get("Wins Added", 0.0)
                )
            else:
                core_score = bowling_role_weight(row["role"]) * acquisition_weight(row["acquisition"]) * (
                    0.24 * radar.get("PP Impact", 0.0)
                    + 0.28 * radar.get("Middle Impact", 0.0)
                    + 0.2 * radar.get("Death Impact", 0.0)
                    + 0.14 * radar.get("Control", 0.0)
                    + 0.14 * radar.get("Wickets", 0.0)
                )
            rows.append(
                {
                    "player": row["player"],
                    "role": row["role"],
                    "core_score": round(core_score, 2),
                    "impact_score": round(float(summary.get("impact_score", 0.0)), 2),
                    "wins_added": round(float(summary.get("wins_added", 0.0)), 2),
                    "phase_identity": profile["style"].get("phase_identity", ""),
                }
            )
        rows.sort(key=lambda item: (item["core_score"], item["wins_added"]), reverse=True)
        return rows[:limit]

    def phase_label(key: str) -> str:
        return {
            "bat_powerplay": "powerplay batting",
            "bat_middle": "middle-overs batting",
            "bat_death": "death batting",
            "bowl_powerplay": "powerplay bowling",
            "bowl_middle": "middle-overs bowling",
            "bowl_death": "death bowling",
        }[key]

    def build_swot(team_code: str, opponent_code: str, venue: str) -> dict[str, list[str]]:
        team = snapshots[team_code]
        opponent = snapshots[opponent_code]
        top_batters = rank_team_players(team_code, "batting", venue, opponent_code, limit=3)
        top_bowlers = rank_team_players(team_code, "bowling", venue, opponent_code, limit=3)
        core_batters = rank_team_core(team_code, "batting", limit=3)
        core_bowlers = rank_team_core(team_code, "bowling", limit=3)
        opp_batters = rank_team_players(opponent_code, "batting", venue, team_code, limit=2)
        opp_bowlers = rank_team_players(opponent_code, "bowling", venue, team_code, limit=2)
        strongest_key = max(
            ["bat_powerplay", "bat_middle", "bat_death", "bowl_powerplay", "bowl_middle", "bowl_death"],
            key=lambda key: team[key],
        )
        weakest_key = min(
            ["bat_powerplay", "bat_middle", "bat_death", "bowl_powerplay", "bowl_middle", "bowl_death"],
            key=lambda key: team[key],
        )
        opponent_best = max(
            ["bat_powerplay", "bat_middle", "bat_death", "bowl_powerplay", "bowl_middle", "bowl_death"],
            key=lambda key: opponent[key],
        )
        venue_profile = venue_profiles.get(venue, {})
        venue_bat_names = {row["player"] for row in venue_profile.get("top_batters", [])}
        venue_bowl_names = {row["player"] for row in venue_profile.get("top_bowlers", [])}
        venue_hits = [row["player"] for row in top_batters + top_bowlers if row["player"] in venue_bat_names or row["player"] in venue_bowl_names]
        strengths = []
        if core_batters:
            strengths.append(
                f"{team_code}'s batting spine is led by {', '.join(row['player'] for row in core_batters[:2])}, which is the safest active base going into {opponent_code} at {venue}."
            )
        if top_batters:
            strengths.append(
                f"The best fixture-specific batting leverage comes from {', '.join(row['player'] for row in top_batters[:2])}, who project most favorably into {opponent_code}'s likely bowling mix."
            )
        elif core_bowlers:
            strengths.append(
                f"The bowling control base is built around {', '.join(row['player'] for row in core_bowlers[:2])}, giving {team_code} a dependable active bowling floor."
            )
        if top_bowlers:
            strengths.append(
                f"The cleanest bowling matchup comes from {', '.join(row['player'] for row in top_bowlers[:2])}, whose active phase profile lines up well against {opponent_code}'s batting core."
            )
        strengths.append(
            f"Venue and matchup scoring still leave {team_code} with an active-core wins-added base of {team['wins_added_total']:.2f}, so the floor remains credible even before fringe players are considered."
        )

        weaknesses = [
            f"{team_code}'s thinnest matchup zone in this fixture is {phase_label(weakest_key)}, which {opponent_code} can attack if the game drifts there.",
            f"{team['no_sample_count']} squad members still sit outside the active evidence set, so the game plan should stay concentrated around the proven core rather than the fringe bench.",
        ]
        if opp_batters:
            weaknesses.append(f"{', '.join(row['player'] for row in opp_batters)} project as the biggest opponent batting threats in this specific matchup.")
        else:
            weaknesses.append("Opponent-specific batting threats are less concentrated, but the uncertainty around low-sample squad pieces still matters.")

        opportunities = [
            f"{team_code} should lean into {phase_label(strongest_key)} because that is where the current matchup matrix gives the clearest edge over {opponent_code}.",
        ]
        if venue_profile.get("avg_total") is not None:
            pace_phase = next((row for row in venue_profile.get("phase_conditions", []) if row["phase"] == "powerplay"), None)
            if pace_phase and pace_phase["run_rate"] >= 9.0:
                opportunities.append(f"{venue} has rewarded early scoring, so {team_code} should look to win the powerplay rather than waiting for a middle-overs reset.")
            else:
                opportunities.append(f"{venue} has not been a pure run-glut venue, so {team_code} can create separation by controlling the quieter phases and forcing {opponent_code} to overhit.")
        if venue_hits:
            opportunities.append(f"Venue history gives extra confidence to {', '.join(venue_hits[:2])} at {venue}, which strengthens the tactical case for using them in their best phase.")
        else:
            opportunities.append(f"There is no dominant venue specialist in the active sample, so {team_code} should trust the matchup edges more than venue folklore.")

        threats = [
            f"{opponent_code}'s biggest live edge in this fixture remains {phase_label(opponent_best)}, and that phase has to be the first item on the defensive brief.",
        ]
        if opp_batters:
            threats.append(f"Opposition batting threat is driven by {', '.join(row['player'] for row in opp_batters)}, whose current matchup scores are strongest into this game.")
        if opp_bowlers:
            threats.append(f"{', '.join(row['player'] for row in opp_bowlers)} can flip the innings with ball in hand if {team_code} lets the contest drift into their best phase windows.")

        return {"strengths": strengths[:3], "weaknesses": weaknesses[:3], "opportunities": opportunities[:3], "threats": threats[:3]}

    def build_tactics(team_code: str, opponent_code: str, venue: str) -> list[str]:
        team = snapshots[team_code]
        top_batters = rank_team_players(team_code, "batting", venue, opponent_code, limit=2)
        core_batters = rank_team_core(team_code, "batting", limit=2)
        top_bowlers = rank_team_players(team_code, "bowling", venue, opponent_code, limit=2)
        opp_batters = rank_team_players(opponent_code, "batting", venue, team_code, limit=2)
        opp_bowlers = rank_team_players(opponent_code, "bowling", venue, team_code, limit=2)
        plans = []
        strongest_bat = max(["bat_powerplay", "bat_middle", "bat_death"], key=lambda key: team[key])
        strongest_bowl = max(["bowl_powerplay", "bowl_middle", "bowl_death"], key=lambda key: team[key])
        if core_batters:
            attack_targets = ", ".join(row["player"] for row in opp_bowlers[:2]) if opp_bowlers else opponent_code
            plans.append(
                f"Batting plan: build the innings around {core_batters[0]['player']}"
                + (
                    f" with {core_batters[1]['player']} as the second scoring pillar"
                    if len(core_batters) > 1
                    else ""
                )
                + f", then use {top_batters[0]['player'] if top_batters else core_batters[0]['player']} as the matchup lever against {attack_targets} in {phase_label(strongest_bat)}."
            )
        if top_bowlers:
            target = opp_batters[0]["player"] if opp_batters else opponent_code
            plans.append(f"Bowling plan: use {top_bowlers[0]['player']} to attack {target} and own {phase_label(strongest_bowl)} before {opponent_code} can settle.")
        venue_profile = venue_profiles.get(venue, {})
        avg_total = venue_profile.get("avg_total")
        if avg_total and avg_total >= 180:
            plans.append(f"Venue plan: {venue} has historically produced {avg_total:.0f}-plus innings, so {team_code} should front-load intent and avoid leaving too much scoring for the final overs.")
        else:
            plans.append(f"Venue plan: {venue} is not purely a free-scoring venue in the sample, so {team_code} should emphasize control, field placement, and matchup discipline over blind acceleration.")
        return plans[:3]

    matches = []
    for idx, match in enumerate(MATCH_SCHEDULE_2026, start=1):
        home = match["home"]
        away = match["away"]
        venue = match["venue"]
        venue_profile = venue_profiles.get(venue, {"avg_total": None, "innings_count": 0, "phase_conditions": [], "top_batters": [], "top_bowlers": []})
        matches.append(
            {
                "match_id": idx,
                "label": f"{home} vs {away}",
                "date": match["date"],
                "start": match["start"],
                "venue": venue,
                "home": home,
                "away": away,
                "venue_profile": venue_profile,
                "home_analysis": {
                    "swot": build_swot(home, away, venue),
                    "tactics": build_tactics(home, away, venue),
                    "top_batters": rank_team_players(home, "batting", venue, away),
                    "top_bowlers": rank_team_players(home, "bowling", venue, away),
                    "active_count": snapshots[home]["active_count"],
                },
                "away_analysis": {
                    "swot": build_swot(away, home, venue),
                    "tactics": build_tactics(away, home, venue),
                    "top_batters": rank_team_players(away, "batting", venue, home),
                    "top_bowlers": rank_team_players(away, "bowling", venue, home),
                    "active_count": snapshots[away]["active_count"],
                },
            }
        )

    teams = {
        team_code: {
            "squad": [
                {
                    "player": canonical_player_name(row["player"]),
                    "acquisition": row["acquisition"],
                    "role": row["role"],
                    "price": row["price"],
                    "active_flag": bool(
                        canonical_player_name(row["player"]) in active_batters
                        or canonical_player_name(row["player"]) in active_bowlers
                    ),
                }
                for row in squad
            ],
            "active_count": snapshots[team_code]["active_count"],
            "no_sample_count": snapshots[team_code]["no_sample_count"],
        }
        for team_code, squad in FINAL_SQUADS_2026.items()
    }

    return {
        "matches": matches,
        "teams": teams,
        "methodology": {
            "summary": (
                "Match Planning combines final 2026 squads with active-player phase impact, skill radar context, wins-added proxies, and venue-level IPL evidence. "
                "Only players with active 2025-tagged evidence are used for the quantitative SWOT and tactical recommendations."
            ),
            "swot": (
                "Strengths and weaknesses are built from team-level active phase snapshots. Opportunities and threats compare each team's strongest active phase windows "
                "with the opponent's softest or strongest phase windows, then layer in venue conditions."
            ),
            "venue": (
                "Venue cards summarize historical run rates, wicket rates, average innings totals, and the strongest active performers at that ground from the ball-by-ball archive."
            ),
        },
    }


def build_batter_diagnostics_payload(players_payload: dict) -> dict:
    ball = pd.read_csv(
        DATA_DIR / "ipl_ball_by_ball.csv",
        parse_dates=["date"],
        usecols=[
            "date",
            "match_id",
            "venue",
            "city",
            "batter",
            "bowler",
            "runs_batter",
            "legal_ball",
            "wicket",
            "dismissal_kind",
            "player_out",
            "phase",
            "balls_remaining",
            "innings_wickets_cum",
        ],
    )
    player_style_lookup = build_dashboard_player_style_lookup()
    ball["batter_name"] = ball["batter"].map(canonical_player_name)
    ball["bowler_name"] = ball["bowler"].map(canonical_player_name)
    ball["bowler_norm"] = ball["bowler"].map(normalize_name)
    ball["bowler_style"] = ball["bowler_norm"].map(
        lambda key: player_style_lookup.get(key, {}).get("bowl_style", "")
    ).replace({"": None})
    ball["bowl_family"] = ball["bowler_style"].map(bowl_family_from_style)
    ball["pressure_state"] = (
        (ball["balls_remaining"] <= 30) | (ball["innings_wickets_cum"] >= 5)
    ).map({True: "High Pressure", False: "Standard"})
    ball["location_key"] = (
        ball["city"]
        .fillna(ball["venue"])
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda value: CITY_ALIASES.get(value, value))
    )
    ball["venue_label"] = (
        ball["city"].fillna(ball["venue"]).astype(str).str.strip().replace({"": "Unknown Venue"})
    )

    batter_profiles = players_payload["batter_profiles"]
    bowler_profiles = players_payload["bowler_profiles"]
    batter_options = sorted(batter_profiles.keys())
    active_batter_options = sorted(
        [
            player
            for player, profile in batter_profiles.items()
            if int(profile["summary"].get("last_year", 0)) >= ACTIVE_CUTOFF_YEAR
        ]
    )
    active_bowler_options = {
        player
        for player, profile in bowler_profiles.items()
        if int(profile["summary"].get("last_year", 0)) >= ACTIVE_CUTOFF_YEAR
    }

    venue_label_lookup = (
        ball.groupby(["location_key", "venue_label"])
        .size()
        .reset_index(name="count")
        .sort_values(["location_key", "count"], ascending=[True, False])
        .drop_duplicates("location_key")
        .set_index("location_key")["venue_label"]
        .to_dict()
    )

    phase_splits = (
        ball.groupby(["batter_name", "phase"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", lambda values: int(values.sum())),
            matches=("match_id", "nunique"),
        )
        .reset_index()
    )
    phase_splits = phase_splits[phase_splits["balls"] >= 12].copy()
    phase_splits["strike_rate"] = phase_splits["runs"] / phase_splits["balls"].clip(lower=1) * 100.0
    phase_splits["dismissal_rate"] = phase_splits["dismissals"] / phase_splits["balls"].clip(lower=1)
    phase_impact_lookup = {
        (player, phase): float(details.get("impact_score", 0.0))
        for player, profile in batter_profiles.items()
        for phase, details in profile.get("phase_details", {}).items()
    }
    phase_splits["impact_score"] = phase_splits.apply(
        lambda row: round(phase_impact_lookup.get((row["batter_name"], row["phase"]), 0.0), 2), axis=1
    )

    pressure_splits = (
        ball.groupby(["batter_name", "pressure_state"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", lambda values: int(values.sum())),
            matches=("match_id", "nunique"),
        )
        .reset_index()
    )
    pressure_splits = pressure_splits[pressure_splits["balls"] >= 12].copy()
    pressure_splits["strike_rate"] = pressure_splits["runs"] / pressure_splits["balls"].clip(lower=1) * 100.0
    pressure_splits["dismissal_rate"] = pressure_splits["dismissals"] / pressure_splits["balls"].clip(lower=1)

    venue_splits = (
        ball.groupby(["batter_name", "location_key"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", lambda values: int(values.sum())),
            matches=("match_id", "nunique"),
        )
        .reset_index()
    )
    venue_splits = venue_splits[venue_splits["balls"] >= 15].copy()
    venue_splits["venue"] = venue_splits["location_key"].map(lambda key: venue_label_lookup.get(key, key.title()))
    venue_splits["strike_rate"] = venue_splits["runs"] / venue_splits["balls"].clip(lower=1) * 100.0
    venue_splits["dismissal_rate"] = venue_splits["dismissals"] / venue_splits["balls"].clip(lower=1)

    venue_pressure_splits = (
        ball[ball["pressure_state"] == "High Pressure"]
        .groupby(["batter_name", "location_key"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", lambda values: int(values.sum())),
            matches=("match_id", "nunique"),
        )
        .reset_index()
    )
    venue_pressure_splits = venue_pressure_splits[venue_pressure_splits["balls"] >= 8].copy()
    venue_pressure_splits["venue"] = venue_pressure_splits["location_key"].map(
        lambda key: venue_label_lookup.get(key, key.title())
    )
    venue_pressure_splits["strike_rate"] = (
        venue_pressure_splits["runs"] / venue_pressure_splits["balls"].clip(lower=1) * 100.0
    )
    venue_pressure_splits["dismissal_rate"] = (
        venue_pressure_splits["dismissals"] / venue_pressure_splits["balls"].clip(lower=1)
    )

    family_splits = (
        ball[ball["bowl_family"].notna()]
        .groupby(["batter_name", "bowl_family"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", lambda values: int(values.sum())),
        )
        .reset_index()
    )
    family_splits = family_splits[family_splits["balls"] >= 20].copy()
    family_splits["strike_rate"] = family_splits["runs"] / family_splits["balls"].clip(lower=1) * 100.0
    family_splits["dismissal_rate"] = family_splits["dismissals"] / family_splits["balls"].clip(lower=1)

    bowler_matchups = (
        ball.groupby(["batter_name", "bowler_name"])
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_ball", "sum"),
            dismissals=("wicket", lambda values: int(values.sum())),
            matches=("match_id", "nunique"),
        )
        .reset_index()
    )
    bowler_matchups = bowler_matchups[bowler_matchups["balls"] >= 8].copy()
    bowler_matchups["strike_rate"] = bowler_matchups["runs"] / bowler_matchups["balls"].clip(lower=1) * 100.0
    bowler_matchups["dismissal_rate"] = bowler_matchups["dismissals"] / bowler_matchups["balls"].clip(lower=1)
    bowler_matchups["attack_score"] = (
        bowler_matchups["strike_rate"] - bowler_matchups["dismissal_rate"] * 140.0 + bowler_matchups["runs"] * 0.15
    )
    bowler_matchups["risk_score"] = (
        bowler_matchups["dismissal_rate"] * 160.0 - bowler_matchups["strike_rate"] * 0.25
    )

    dismissal_modes = (
        ball[(ball["player_out"] == ball["batter"]) & (ball["dismissal_kind"].notna())]
        .groupby(["batter_name", "dismissal_kind"])
        .agg(count=("dismissal_kind", "size"))
        .reset_index()
    )
    dismissal_totals = dismissal_modes.groupby("batter_name")["count"].sum().to_dict()
    dismissal_modes["share"] = dismissal_modes.apply(
        lambda row: row["count"] / max(int(dismissal_totals.get(row["batter_name"], 1)), 1),
        axis=1,
    )

    summaries = {}
    for player, profile in batter_profiles.items():
        summary = profile.get("summary", {})
        summaries[player] = {
            "player": player,
            "runs": int(summary.get("runs", 0)),
            "balls": int(summary.get("balls", 0)),
            "matches": int(summary.get("matches", 0)),
            "strike_rate": round(float(summary.get("strike_rate", 0.0)), 2),
            "wins_added": round(float(summary.get("wins_added", 0.0)), 2),
            "impact_score": round(float(summary.get("impact_score", 0.0)), 2),
            "last_year": int(summary.get("last_year", 0)),
            "active": int(summary.get("last_year", 0)) >= ACTIVE_CUTOFF_YEAR,
            "style": profile.get("style", {}),
        }

    return {
        "batter_options": batter_options,
        "active_batter_options": active_batter_options,
        "summaries": summaries,
        "active_bowler_options": sorted(active_bowler_options),
        "phase_splits": phase_splits.to_dict("records"),
        "pressure_splits": pressure_splits.to_dict("records"),
        "venue_splits": venue_splits.to_dict("records"),
        "venue_pressure_splits": venue_pressure_splits.to_dict("records"),
        "family_splits": family_splits.to_dict("records"),
        "bowler_matchups": bowler_matchups.to_dict("records"),
        "dismissal_modes": dismissal_modes.sort_values(["batter_name", "count"], ascending=[True, False]).to_dict("records"),
        "methodology": {
            "summary": (
                "Batter Diagnostics is the maximum scouting layer available from the current Cricsheet-style IPL ball-by-ball sample. "
                "It identifies where a batter scores best by phase, pressure state, venue, bowling family, named bowlers, and dismissal mode."
            ),
            "limitations": (
                "This dataset does not contain Hawkeye-style attributes such as line, length, swing, seam movement, or shot coordinates. "
                "So the module shows condition-based strengths and weaknesses rather than exact pitch-map or wagon-wheel zones."
            ),
        },
    }


def build_salary_value_payload(players_payload: dict) -> dict:
    salaries = pd.read_csv(DATA_DIR / "ipl_salaries_2026.csv")
    salaries["player"] = (
        salaries["player_name_raw"]
        .astype(str)
        .str.replace("*", "", regex=False)
        .str.replace("(T)", "", regex=False)
        .str.strip()
        .map(canonical_player_name)
    )

    squad_lookup = {
        canonical_player_name(entry["player"]): {"team_code": team_code, "role": entry["role"]}
        for team_code, squad in FINAL_SQUADS_2026.items()
        for entry in squad
    }

    batter_profiles = players_payload["batter_profiles"]
    bowler_profiles = players_payload["bowler_profiles"]

    rows = []
    for _, salary_row in salaries.iterrows():
        player = salary_row["player"]
        batter = batter_profiles.get(player)
        bowler = bowler_profiles.get(player)
        last_year = max(
            int((batter or {}).get("summary", {}).get("last_year", 0)),
            int((bowler or {}).get("summary", {}).get("last_year", 0)),
        )
        if last_year < ACTIVE_CUTOFF_YEAR:
            continue

        batting_summary = (batter or {}).get("summary", {})
        bowling_summary = (bowler or {}).get("summary", {})
        squad_meta = squad_lookup.get(player, {})
        role = str(squad_meta.get("role", "") or "").lower()
        batting_balls = int(batting_summary.get("balls", 0))
        bowling_balls = int(bowling_summary.get("balls", 0))
        has_batting_signal = batter is not None and batting_balls >= 60
        has_bowling_signal = bowler is not None and bowling_balls >= 60
        if "wicketkeeper" in role:
            role_group = "Wicketkeeper"
        elif "all-rounder" in role:
            role_group = "All-rounder"
        elif "bowler" in role:
            role_group = "Bowler"
        elif "batter" in role:
            role_group = "Batter"
        elif has_batting_signal and has_bowling_signal:
            role_group = "All-rounder"
        elif has_bowling_signal:
            role_group = "Bowler"
        else:
            role_group = "Batter"

        batting_impact = float(batting_summary.get("impact_score", 0.0)) if has_batting_signal else 0.0
        bowling_impact = float(bowling_summary.get("impact_score", 0.0)) if has_bowling_signal else 0.0
        batting_wins = float(batting_summary.get("wins_added", 0.0)) if has_batting_signal else 0.0
        bowling_wins = float(bowling_summary.get("wins_added", 0.0)) if has_bowling_signal else 0.0
        total_impact = batting_impact + bowling_impact
        total_wins = batting_wins + bowling_wins
        matches = max(int(batting_summary.get("matches", 0)), int(bowling_summary.get("matches", 0)))
        batting_phase_peaks = [float(item.get("value", 0.0)) for item in (batter or {}).get("radar", [])[:3]] if has_batting_signal else []
        bowling_phase_peaks = [float(item.get("value", 0.0)) for item in (bowler or {}).get("radar", [])[:3]] if has_bowling_signal else []
        peak_phase_pct = max(batting_phase_peaks + bowling_phase_peaks + [0.0])
        rows.append(
            {
                "player": player,
                "team_code": squad_meta.get("team_code", salary_row["team_code"]),
                "role_group": role_group,
                "salary_cr": float(salary_row["salary_cr"]),
                "salary_lakh": int(salary_row["salary_lakh"]),
                "is_overseas": int(salary_row["is_overseas_flag"]),
                "trade_marker": int(salary_row["trade_marker"]),
                "batting_impact": batting_impact,
                "bowling_impact": bowling_impact,
                "total_impact": total_impact,
                "batting_wins_added": batting_wins,
                "bowling_wins_added": bowling_wins,
                "total_wins_added": total_wins,
                "matches": matches,
                "peak_phase_pct": peak_phase_pct,
                "has_batting": int(has_batting_signal),
                "has_bowling": int(has_bowling_signal),
            }
        )

    value_df = pd.DataFrame(rows)
    if value_df.empty:
        return {"players": [], "teams": [], "methodology": {}}

    def pct(series: pd.Series) -> pd.Series:
        return series.rank(pct=True).fillna(0.0)

    value_df["impact_pct"] = pct(value_df["total_impact"])
    value_df["wins_pct"] = pct(value_df["total_wins_added"])
    value_df["matches_pct"] = pct(value_df["matches"])
    value_df["peak_pct"] = pct(value_df["peak_phase_pct"])
    value_df["performance_score"] = (
        100
        * (
            0.34 * value_df["impact_pct"]
            + 0.34 * value_df["wins_pct"]
            + 0.16 * value_df["matches_pct"]
            + 0.16 * value_df["peak_pct"]
        )
    )

    X = pd.DataFrame(
        {
            "impact_pct": value_df["impact_pct"],
            "wins_pct": value_df["wins_pct"],
            "matches_pct": value_df["matches_pct"],
            "peak_pct": value_df["peak_pct"],
            "has_bowling": value_df["has_bowling"],
            "is_overseas": value_df["is_overseas"],
            "trade_marker": value_df["trade_marker"],
        }
    )
    role_dummies = pd.get_dummies(value_df["role_group"], prefix="role", dtype=float)
    X = pd.concat([X, role_dummies], axis=1)
    X.insert(0, "intercept", 1.0)
    y = np.log1p(value_df["salary_cr"].clip(lower=0.3))
    beta, *_ = np.linalg.lstsq(X.to_numpy(dtype=float), y.to_numpy(dtype=float), rcond=None)
    predicted = X.to_numpy(dtype=float) @ beta
    value_df["fair_value_cr"] = np.maximum(np.expm1(predicted), 0.3)
    value_df["value_gap_cr"] = value_df["fair_value_cr"] - value_df["salary_cr"]
    value_df["salary_value_index"] = 100.0 * value_df["fair_value_cr"] / value_df["salary_cr"].clip(lower=0.3)
    gap_scale = max(float(value_df["value_gap_cr"].std()), 0.75)
    value_df["valuation_score"] = 50.0 + 28.0 * np.tanh(value_df["value_gap_cr"] / gap_scale)

    def value_band(row: pd.Series) -> str:
        if row["salary_value_index"] >= 120 and row["value_gap_cr"] >= 1.0:
            return "Undervalued"
        if row["salary_value_index"] <= 80 and row["value_gap_cr"] <= -1.0:
            return "Overvalued"
        return "Fair Value"

    value_df["valuation_band"] = value_df.apply(value_band, axis=1)

    def explain_row(row: pd.Series) -> str:
        strengths = []
        if row["impact_pct"] >= 0.8:
            strengths.append("elite impact profile")
        if row["wins_pct"] >= 0.8:
            strengths.append("strong wins-added record")
        if row["matches_pct"] >= 0.8:
            strengths.append("deep IPL sample")
        if row["peak_pct"] >= 0.8:
            strengths.append("high phase ceiling")
        strength_text = ", ".join(strengths[:2]) if strengths else "mixed performance profile"
        if row["valuation_band"] == "Undervalued":
            return f"Current salary looks light relative to a {strength_text}."
        if row["valuation_band"] == "Overvalued":
            return f"Current salary is rich versus a {strength_text}."
        return f"Current salary broadly tracks a {strength_text}."

    value_df["explanation"] = value_df.apply(explain_row, axis=1)

    team_summary = (
        value_df.groupby("team_code")
        .agg(
            avg_value_index=("salary_value_index", "mean"),
            total_gap_cr=("value_gap_cr", "sum"),
            undervalued_count=("valuation_band", lambda values: int((pd.Series(values) == "Undervalued").sum())),
            overvalued_count=("valuation_band", lambda values: int((pd.Series(values) == "Overvalued").sum())),
        )
        .reset_index()
        .round({"avg_value_index": 1, "total_gap_cr": 2})
        .sort_values(["total_gap_cr", "avg_value_index"], ascending=[False, False])
    )

    player_records = (
        value_df.sort_values(["salary_value_index", "performance_score"], ascending=[False, False])
        .round(
            {
                "salary_cr": 2,
                "fair_value_cr": 2,
                "value_gap_cr": 2,
                "salary_value_index": 1,
                "valuation_score": 1,
                "performance_score": 1,
                "total_impact": 2,
                "total_wins_added": 2,
            }
        )
        .to_dict("records")
    )

    return {
        "players": player_records,
        "teams": team_summary.to_dict("records"),
        "top_undervalued": [row for row in player_records if row["valuation_band"] == "Undervalued"][:15],
        "top_overvalued": [row for row in value_df.sort_values(["salary_value_index", "performance_score"]).round(
            {
                "salary_cr": 2,
                "fair_value_cr": 2,
                "value_gap_cr": 2,
                "salary_value_index": 1,
                "valuation_score": 1,
                "performance_score": 1,
                "total_impact": 2,
                "total_wins_added": 2,
            }
        ).to_dict("records") if row["valuation_band"] == "Overvalued"][:15],
        "methodology": {
            "summary": (
                "Salary Value uses current 2026 player salaries from the salary sheet and compares them with a model-implied fair salary built from all IPL performance available "
                "through the ball-by-ball archive. The model uses total impact score, wins-added proxy, IPL sample depth, phase ceiling, role, overseas status, and all-round value."
            ),
            "index": (
                "Salary Value Index = 100 x Fair Salary / Current Salary. Scores above 100 indicate a player is cheaper than his model-implied fair value; "
                "scores below 100 indicate he is expensive relative to performance."
            ),
            "gap": (
                "Value Gap is measured in crores and equals Fair Salary minus Current Salary. Positive gaps indicate undervaluation; negative gaps indicate overvaluation."
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
    players_payload = build_player_payload()
    payload = {
        "overview": build_overview_payload(),
        "phase_rankings": build_phase_payload(),
        "auction": build_auction_payload(),
        "teams": build_team_payload(),
        "players": players_payload,
        "scenario": build_scenario_payload(),
        "matchups": build_matchup_payload(),
        "batter_diagnostics": build_batter_diagnostics_payload(players_payload),
        "salary_value": build_salary_value_payload(players_payload),
        "match_planning": build_match_planning_payload(players_payload),
        "story": build_story_payload(),
    }
    js = "window.DASHBOARD_DATA = " + json.dumps(payload, indent=2) + ";\n"
    (OUT_DIR / "dashboard_data.js").write_text(js)
    print("Wrote", OUT_DIR / "dashboard_data.js")


if __name__ == "__main__":
    main()
