from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
import random
import re
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"

DEFAULT_AUCTION_FORMAT = {
    "squad_size": 25,
    "overseas_limit": 8,
}

ROLE_NEED_EQUIVALENTS = {
    "indian_spin": {"spin_bowler": 0.95, "spin_all_rounder": 0.35},
    "spin_bowler": {"indian_spin": 0.90, "spin_all_rounder": 0.35},
    "overseas_pace": {"domestic_pace": 0.35, "seam_all_rounder": 0.20},
    "domestic_pace": {"overseas_pace": 0.45, "seam_all_rounder": 0.20},
    "middle_bat": {"domestic_bat_depth": 0.45, "top_order_bat": 0.20},
    "domestic_bat_depth": {"middle_bat": 0.55, "top_order_bat": 0.15},
}


BASE_TEAM_CONFIGS = {
    "RR": {
        "name": "Rajasthan Royals",
        "purse": 16.05,
        "spent": 108.95,
        "retained": 16,
        "overseas_retained": 7,
        "retained_players": [
            "Dhruv Jurel",
            "Donovan Ferreira",
            "Jofra Archer",
            "Kwena Maphaka",
            "Lhuan-Dre Pretorious",
            "Nandre Burger",
            "Ravindra Jadeja",
            "Riyan Parag",
            "Sam Curran",
            "Sandeep Sharma",
            "Shimron Hetmyer",
            "Shubham Dubey",
            "Tushar Deshpande",
            "Vaibhav Suryavanshi",
            "Yashaswi Jaiswal",
            "Yudhvir Charak",
        ],
        "max_buys": 4,
        "min_buys": 2,
        "role_caps": {
            "indian_spin": 6.50,
            "overseas_pace": 3.25,
            "domestic_pace": 0.90,
            "domestic_bat_depth": 0.60,
            "domestic_all_rounder": 0.60,
            "wicketkeeper": 0.40,
        },
        "role_needs": {
            "indian_spin": 1.30,
            "overseas_pace": 1.10,
            "domestic_pace": 0.75,
            "domestic_bat_depth": 0.45,
            "domestic_all_rounder": 0.35,
            "wicketkeeper": 0.10,
        },
        "focus_strategy": {
            "singleton_roles": ["indian_spin", "overseas_pace", "domestic_bat_depth"],
            "core_roles": ["indian_spin", "overseas_pace"],
            "non_core_hold_until_set": 14,
            "late_stage_set": 30,
            "late_stage_min_quality": 0.24,
            "premium_reserve_roles": ["indian_spin", "overseas_pace"],
            "premium_reserve_discount": 0.65,
            "priority_target_bonus": 1.18,
            "priority_target_reserve_floor": 1.5,
            "overseas_early_set_cutoff": 12,
            "overseas_very_early_set_cutoff": 4,
            "overseas_early_discount": 0.42,
            "overseas_very_early_discount": 0.72,
            "overseas_right_arm_fast_bonus": 1.12,
            "overseas_left_arm_discount": 0.84,
            "domestic_bat_requires_spin": True,
        },
    },
    "CSK": {
        "name": "Chennai Super Kings",
        "purse": 43.40,
        "spent": 81.60,
        "retained": 16,
        "overseas_retained": 4,
        "retained_players": [
            "Anshul Kamboj", "Gurjapneet Singh", "Jamie Overton", "MS Dhoni",
            "Mukesh Choudhary", "Nathan Ellis", "Noor Ahmad", "Ramakrishna Ghosh",
            "Sanju Samson", "Ruturaj Gaikwad", "Shivam Dube", "Shreyas Gopal",
            "Syed Khaleel Ahmed", "Ayush Mhatre", "Dewald Brevis", "Urvil Patel",
        ],
        "role_needs": {
            "top_order_bat": 0.75,
            "middle_bat": 0.60,
            "domestic_pace": 0.90,
            "overseas_pace": 0.95,
            "spin_all_rounder": 0.12,
            "spin_bowler": 0.12,
            "wicketkeeper": 0.05,
        },
        "focus_strategy": {
            "singleton_roles": ["wicketkeeper"],
            "core_roles": ["domestic_pace", "overseas_pace"],
            "non_core_hold_until_set": 8,
            "late_stage_set": 30,
            "late_stage_min_quality": 0.20,
            "premium_reserve_roles": ["domestic_pace", "overseas_pace"],
            "premium_reserve_discount": 0.75
        }
    },
    "DC": {
        "name": "Delhi Capitals",
        "purse": 21.80,
        "spent": 103.20,
        "retained": 17,
        "overseas_retained": 3,
        "retained_players": [
            "Abhishek Porel", "Ajay Mandal", "Ashutosh Sharma", "Axar Patel",
            "Dushmantha Chameera", "Karun Nair", "KL Rahul", "Kuldeep Yadav",
            "Madhav Tiwari", "Mitchell Starc", "Mukesh Kumar", "Nitish Rana",
            "Sameer Rizvi", "T. Natarajan", "Tripurana Vijay", "Tristan Stubbs",
            "Vipraj Nigam",
        ],
        "role_needs": {
            "top_order_bat": 0.45,
            "middle_bat": 0.55,
            "finisher": 0.30,
            "wicketkeeper": 0.05,
            "overseas_pace": 0.35,
            "domestic_pace": 0.40,
            "spin_bowler": 0.08,
        },
    },
    "GT": {
        "name": "Gujarat Titans",
        "purse": 12.90,
        "spent": 112.10,
        "retained": 20,
        "overseas_retained": 4,
        "retained_players": [
            "Anuj Rawat", "Glenn Phillips", "Gurnoor Singh Brar", "Ishant Sharma",
            "Jayant Yadav", "Jos Buttler", "Kagiso Rabada", "Kumar Kushagra",
            "Manav Suthar", "Mohammad Siraj", "Mohd. Arshad Khan", "Nishant Sindhu",
            "Prasidh Krishna", "R. Sai Kishore", "Rahul Tewatia", "Rashid Khan",
            "Sai Sudharsan", "Shahrukh Khan", "Shubman Gill", "Washington Sundar",
        ],
        "role_needs": {
            "wicketkeeper": 0.25,
            "middle_bat": 0.40,
            "domestic_pace": 0.20,
            "overseas_pace": 0.20,
            "domestic_bat_depth": 0.20,
            "spin_bowler": 0.02,
        },
    },
    "KKR": {
        "name": "Kolkata Knight Riders",
        "purse": 64.30,
        "spent": 60.70,
        "retained": 12,
        "overseas_retained": 2,
        "retained_players": [
            "Ajinkya Rahane", "Angkrish Raghuvanshi", "Anukul Roy", "Harshit Rana",
            "Manish Pandey", "Ramandeep Singh", "Rinku Singh", "Rovman Powell",
            "Sunil Narine", "Umran Malik", "Vaibhav Arora", "Varun Chakaravarthy",
        ],
        "role_needs": {
            "wicketkeeper": 0.95,
            "top_order_bat": 0.75,
            "finisher": 0.65,
            "overseas_pace": 0.95,
            "domestic_pace": 0.70,
            "spin_bowler": 0.05,
            "seam_all_rounder": 0.55,
        },
    },
    "LSG": {
        "name": "Lucknow Super Giants",
        "purse": 22.95,
        "spent": 102.05,
        "retained": 19,
        "overseas_retained": 4,
        "retained_players": [
            "Abdul Samad", "Aiden Markram", "Akash Singh", "Arjun Tendulkar",
            "Arshin Kulkarni", "Avesh Khan", "Ayush Badoni", "Digvesh Rathi",
            "Himmat Singh", "Manimaran Siddharth", "Matthew Breetzke", "Mayank Yadav",
            "Md Shami", "Mitchell Marsh", "Mohsin Khan", "Nicholas Pooran",
            "Prince Yadav", "Rishabh Pant", "Shahbaz Ahmed",
        ],
        "role_needs": {
            "wicketkeeper": 0.00,
            "overseas_pace": 0.45,
            "domestic_pace": 0.65,
            "spin_bowler": 0.18,
            "top_order_bat": 0.20,
        },
    },
    "MI": {
        "name": "Mumbai Indians",
        "purse": 2.75,
        "spent": 122.25,
        "retained": 20,
        "overseas_retained": 7,
        "retained_players": [
            "Allah Ghazanfar", "Ashwani Kumar", "Corbin Bosch", "Deepak Chahar",
            "Hardik Pandya", "Jasprit Bumrah", "Mayank Markande", "Mitchell Santner",
            "Naman Dhir", "Raghu Sharma", "Raj Angad Bawa", "Robin Minz",
            "Rohit Sharma", "Ryan Rickelton", "Shardul Thakur", "Sherfane Rutherford",
            "Suryakumar Yadav", "Tilak Verma", "Trent Boult", "Will Jacks",
        ],
        "role_needs": {
            "domestic_pace": 0.30,
            "domestic_bat_depth": 0.25,
            "wicketkeeper": 0.20,
            "spin_bowler": 0.02,
        },
    },
    "PBKS": {
        "name": "Punjab Kings",
        "purse": 11.50,
        "spent": 113.50,
        "retained": 21,
        "overseas_retained": 6,
        "retained_players": [
            "Arshdeep Singh", "Azmatullah Omarzai", "Harnoor Pannu", "Harpreet Brar",
            "Lockie Ferguson", "Marco Jansen", "Marcus Stoinis", "Mitch Owen",
            "Musheer Khan", "Nehal Wadhera", "Prabhsimran Singh", "Priyansh Arya",
            "Pyla Avinash", "Shashank Singh", "Shreyas Iyer", "Suryansh Shedge",
            "Vishnu Vinod", "Vyshak Vijaykumar", "Xavier Bartlett", "Yash Thakur",
            "Yuzvendra Chahal",
        ],
        "role_needs": {
            "spin_bowler": 0.02,
            "wicketkeeper": 0.35,
            "domestic_bat_depth": 0.30,
            "top_order_bat": 0.20,
        },
    },
    "RCB": {
        "name": "Royal Challengers Bengaluru",
        "purse": 16.40,
        "spent": 108.60,
        "retained": 17,
        "overseas_retained": 6,
        "retained_players": [
            "Abhinandan Singh", "Bhuvneshwar Kumar", "Devdutt Padikkal", "Jacob Bethell",
            "Jitesh Sharma", "Josh Hazlewood", "Krunal Pandya", "Nuwan Thushara",
            "Phil Salt", "Rajat Patidar", "Rasikh Dar", "Romario Shepherd",
            "Suyash Sharma", "Swapnil Singh", "Tim David", "Virat Kohli", "Yash Dayal",
        ],
        "role_needs": {
            "spin_bowler": 0.18,
            "domestic_pace": 0.35,
            "top_order_bat": 0.20,
            "middle_bat": 0.25,
            "wicketkeeper": 0.05,
        },
    },
    "SRH": {
        "name": "Sunrisers Hyderabad",
        "purse": 25.50,
        "spent": 99.50,
        "retained": 15,
        "overseas_retained": 6,
        "retained_players": [
            "Abhishek Sharma", "Aniket Verma", "Brydon Carse", "Eshan Malinga",
            "Harsh Dubey", "Harshal Patel", "Heinrich Klaasen", "Ishan Kishan",
            "Jaydev Unadkat", "Kamindu Mendis", "Nitish Kumar Reddy", "Pat Cummins",
            "Smaran Ravichandaran", "Travis Head", "Zeeshan Ansari",
        ],
        "role_needs": {
            "spin_bowler": 0.16,
            "domestic_pace": 0.60,
            "middle_bat": 0.25,
            "wicketkeeper": 0.05,
            "overseas_pace": 0.35,
        },
    },
}

DEFAULT_AUCTION_FILES = {
    "2026": DATA_DIR / "ipl_auction_2026_full.xlsx",
}

DEFAULT_SOLD_FILES = {
    "2026": DATA_DIR / "IPL_Auction_2026_Sold_Player.csv",
}

# Backward-compatible alias for existing imports.
TEAM_CONFIGS = BASE_TEAM_CONFIGS


ACTUAL_TEAM_PURCHASES = {
    "RR": {
        "Ravi Bishnoi": "core target won",
        "Adam Milne": "overseas fast-bowling target won",
    }
}

TEAM_PRIORITY_TARGETS = {
    "RR": {
        "indian_spin": "ravi bishnoi",
        "overseas_pace": "a milne",
    }
}


NAME_FIXES = {
    # Rajasthan Royals and common auction targets
    "ybk jaiswal": "yashaswi jaiswal",
    "yashaswi jaiswal": "yashaswi jaiswal",
    "jc archer": "jofra archer",
    "jofra archer": "jofra archer",
    "ra jadeja": "ravindra jadeja",
    "ravindra jadeja": "ravindra jadeja",
    "r parag": "riyan parag",
    "riyan parag": "riyan parag",
    "sm curran": "sam curran",
    "sam curran": "sam curran",
    "so hetmyer": "shimron hetmyer",
    "shimron hetmyer": "shimron hetmyer",
    "tu deshpande": "tushar deshpande",
    "tushar deshpande": "tushar deshpande",
    "kt maphaka": "kwena maphaka",
    "kwena maphaka": "kwena maphaka",
    "d ferreira": "donovan ferreira",
    "donovan ferreira": "donovan ferreira",
    "sb dubey": "shubham dubey",
    "shubham dubey": "shubham dubey",
    "n burger": "nandre burger",
    "nandre burger": "nandre burger",
    "v suryavanshi": "vaibhav suryavanshi",
    "vaibhav suryavanshi": "vaibhav suryavanshi",
    "a milne": "adam milne",
    "adam milne": "adam milne",
    "fazalhaq farooqi": "fazalhaq farooqi",
    "rahmanullah gurbaz": "rahmanullah gurbaz",
    "r chahar": "rahul chahar",
    "rahul chahar": "rahul chahar",
    "r bishnoi": "ravi bishnoi",
    "ravi bishnoi": "ravi bishnoi",

    # CSK
    "a kamboj": "anshul kamboj",
    "anshul kamboj": "anshul kamboj",
    "j overton": "jamie overton",
    "jamie overton": "jamie overton",
    "nt ellis": "nathan ellis",
    "nathan ellis": "nathan ellis",
    "sv samson": "sanju samson",
    "sanju samson": "sanju samson",
    "rd gaikwad": "ruturaj gaikwad",
    "ruturaj gaikwad": "ruturaj gaikwad",
    "s dube": "shivam dube",
    "shivam dube": "shivam dube",
    "s gopal": "shreyas gopal",
    "shreyas gopal": "shreyas gopal",
    "d brevis": "dewald brevis",
    "dewald brevis": "dewald brevis",
    "a mhatre": "ayush mhatre",
    "ayush mhatre": "ayush mhatre",
    "noor ahmad": "noor ahmad",
    "urvil patel": "urvil patel",

    # DC
    "abishek porel": "abhishek porel",
    "ic porel": "abhishek porel",
    "abhishek porel": "abhishek porel",
    "pvd chameera": "dushmantha chameera",
    "dushmantha chameera": "dushmantha chameera",
    "kk nair": "karun nair",
    "karun nair": "karun nair",
    "ma starc": "mitchell starc",
    "mitchell starc": "mitchell starc",
    "t natarajan": "t natarajan",
    "t natarajan": "t natarajan",
    "t stubbs": "tristan stubbs",
    "tristan stubbs": "tristan stubbs",
    "v nigam": "vipraj nigam",
    "vipraj nigam": "vipraj nigam",
    "nitish rana": "nitish rana",
    "n rana": "nitish rana",
    "kl rahul": "kl rahul",
    "axar patel": "axar patel",

    # GT
    "jc buttler": "jos buttler",
    "j buttler": "jos buttler",
    "jos buttler": "jos buttler",
    "gd phillips": "glenn phillips",
    "glenn phillips": "glenn phillips",
    "gurnoor brar": "gurnoor singh brar",
    "gurnoor singh brar": "gurnoor singh brar",
    "k rabada": "kagiso rabada",
    "kagiso rabada": "kagiso rabada",
    "mohammed siraj": "mohammad siraj",
    "mohammad siraj": "mohammad siraj",
    "arshad khan": "mohd arshad khan",
    "mohd arshad khan": "mohd arshad khan",
    "m prasidh krishna": "prasidh krishna",
    "prasidh krishna": "prasidh krishna",
    "r sai kishore": "r sai kishore",
    "r tewatia": "rahul tewatia",
    "rahul tewatia": "rahul tewatia",
    "b sai sudharsan": "sai sudharsan",
    "sai sudharsan": "sai sudharsan",
    "m shahrukh khan": "shahrukh khan",
    "shahrukh khan": "shahrukh khan",

    # KKR
    "am rahane": "ajinkya rahane",
    "ajinkya rahane": "ajinkya rahane",
    "a raghuvanshi": "angkrish raghuvanshi",
    "angkrish raghuvanshi": "angkrish raghuvanshi",
    "mk pandey": "manish pandey",
    "manish pandey": "manish pandey",
    "r powell": "rovman powell",
    "rovman powell": "rovman powell",
    "sp narine": "sunil narine",
    "sunil narine": "sunil narine",
    "vg arora": "vaibhav arora",
    "vaibhav arora": "vaibhav arora",
    "varun chakaravarthy": "varun chakaravarthy",

    # LSG
    "ak markram": "aiden markram",
    "aiden markram": "aiden markram",
    "a badoni": "ayush badoni",
    "ayush badoni": "ayush badoni",
    "ds rathi": "digvesh rathi",
    "digvesh rathi": "digvesh rathi",
    "m siddharth": "manimaran siddharth",
    "manimaran siddharth": "manimaran siddharth",
    "mp breetzke": "matthew breetzke",
    "matthew breetzke": "matthew breetzke",
    "mohammed shami": "md shami",
    "md shami": "md shami",
    "mr marsh": "mitchell marsh",
    "mitchell marsh": "mitchell marsh",
    "n pooran": "nicholas pooran",
    "nicholas pooran": "nicholas pooran",
    "rr pant": "rishabh pant",
    "rishabh pant": "rishabh pant",

    # MI
    "dl chahar": "deepak chahar",
    "rd chahar": "deepak chahar",
    "deepak chahar": "deepak chahar",
    "hh pandya": "hardik pandya",
    "hardik pandya": "hardik pandya",
    "kh pandya": "krunal pandya",
    "krunal pandya": "krunal pandya",
    "jj bumrah": "jasprit bumrah",
    "jasprit bumrah": "jasprit bumrah",
    "m markande": "mayank markande",
    "mayank markande": "mayank markande",
    "mj santner": "mitchell santner",
    "mitchell santner": "mitchell santner",
    "ra bawa": "raj angad bawa",
    "raj angad bawa": "raj angad bawa",
    "r minz": "robin minz",
    "robin minz": "robin minz",
    "rd rickelton": "ryan rickelton",
    "ryan rickelton": "ryan rickelton",
    "se rutherford": "sherfane rutherford",
    "sherfane rutherford": "sherfane rutherford",
    "ta boult": "trent boult",
    "trent boult": "trent boult",
    "wg jacks": "will jacks",
    "will jacks": "will jacks",

    # PBKS
    "lh ferguson": "lockie ferguson",
    "lockie ferguson": "lockie ferguson",
    "m jansen": "marco jansen",
    "marco jansen": "marco jansen",
    "mp stoinis": "marcus stoinis",
    "marcus stoinis": "marcus stoinis",
    "mj owen": "mitch owen",
    "mitch owen": "mitch owen",
    "n wadhera": "nehal wadhera",
    "nehal wadhera": "nehal wadhera",
    "ss iyer": "shreyas iyer",
    "shreyas iyer": "shreyas iyer",
    "dp vijaykumar": "vyshak vijaykumar",
    "vyshak vijaykumar": "vyshak vijaykumar",
    "xc bartlett": "xavier bartlett",
    "xavier bartlett": "xavier bartlett",
    "ys chahal": "yuzvendra chahal",
    "yuzvendra chahal": "yuzvendra chahal",

    # RCB
    "d padikkal": "devdutt padikkal",
    "devdutt padikkal": "devdutt padikkal",
    "jg bethell": "jacob bethell",
    "jacob bethell": "jacob bethell",
    "jr hazlewood": "josh hazlewood",
    "josh hazlewood": "josh hazlewood",
    "n thushara": "nuwan thushara",
    "t thushara": "nuwan thushara",
    "nuwan thushara": "nuwan thushara",
    "pd salt": "phil salt",
    "phil salt": "phil salt",
    "rm patidar": "rajat patidar",
    "rajat patidar": "rajat patidar",
    "r shepherd": "romario shepherd",
    "romario shepherd": "romario shepherd",
    "th david": "tim david",
    "tim david": "tim david",
    "v kohli": "virat kohli",
    "virat kohli": "virat kohli",

    # SRH
    "e malinga": "eshan malinga",
    "eshan malinga": "eshan malinga",
    "h klaasen": "heinrich klaasen",
    "heinrich klaasen": "heinrich klaasen",
    "jd unadkat": "jaydev unadkat",
    "jaydev unadkat": "jaydev unadkat",
    "nithish kumar reddy": "nitish kumar reddy",
    "nitish kumar reddy": "nitish kumar reddy",
    "pj cummins": "pat cummins",
    "pat cummins": "pat cummins",
    "tm head": "travis head",
    "travis head": "travis head",

    # Wider T20 names used elsewhere in the model
    "r ravindra": "rachin ravindra",
    "rachin ravindra": "rachin ravindra",
    "da miller": "david miller",
    "david miller": "david miller",
    "m pathirana": "matheesha pathirana",
    "matheesha pathirana": "matheesha pathirana",
    "w hasaranga": "wanindu hasaranga",
    "wanindu hasaranga": "wanindu hasaranga",
    "q de kock": "quinton de kock",
    "quinton de kock": "quinton de kock",
    "vr iyer": "venkatesh iyer",
    "venkatesh iyer": "venkatesh iyer",
}


@dataclass
class TeamState:
    code: str
    purse: float
    spent: float
    retained: int
    overseas_retained: int
    squad_size: int
    overseas_limit: int
    aggression: float
    role_needs: dict[str, float]
    role_caps: dict[str, float]
    focus_strategy: dict[str, Any]
    max_buys: int
    min_buys: int
    purchases: list[dict[str, Any]] = field(default_factory=list)
    role_counts: dict[str, int] = field(default_factory=dict)

    @property
    def overseas_slots_left(self) -> int:
        bought_overseas = sum(1 for p in self.purchases if p["is_overseas"])
        return max(0, self.overseas_limit - self.overseas_retained - bought_overseas)

    @property
    def buys_left(self) -> int:
        return max(0, self.max_buys - len(self.purchases))

    @property
    def auction_power(self) -> float:
        open_slots = max(1, self.squad_size - self.retained)
        purse_per_slot = self.purse / open_slots
        return round(self.aggression * purse_per_slot, 3)


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return NAME_FIXES.get(name, name)


DISPLAY_NAME_FIXES = {
    "ms dhoni": "MS Dhoni",
    "kl rahul": "KL Rahul",
    "t natarajan": "T. Natarajan",
    "r sai kishore": "R. Sai Kishore",
    "md shami": "Md Shami",
    "mohd arshad khan": "Mohd. Arshad Khan",
    "yashaswi jaiswal": "Yashaswi Jaiswal",
    "donovan ferreira": "Donovan Ferreira",
    "jofra archer": "Jofra Archer",
    "kwena maphaka": "Kwena Maphaka",
    "lhuan dre pretorious": "Lhuan-Dre Pretorious",
    "nandre burger": "Nandre Burger",
    "ravindra jadeja": "Ravindra Jadeja",
    "riyan parag": "Riyan Parag",
    "sam curran": "Sam Curran",
    "shimron hetmyer": "Shimron Hetmyer",
    "tushar deshpande": "Tushar Deshpande",
    "vaibhav suryavanshi": "Vaibhav Suryavanshi",
    "yudhvir charak": "Yudhvir Charak",
    "jamie overton": "Jamie Overton",
    "nathan ellis": "Nathan Ellis",
    "sanju samson": "Sanju Samson",
    "ruturaj gaikwad": "Ruturaj Gaikwad",
    "shivam dube": "Shivam Dube",
    "shreyas gopal": "Shreyas Gopal",
    "dewald brevis": "Dewald Brevis",
    "abhishek porel": "Abhishek Porel",
    "dushmantha chameera": "Dushmantha Chameera",
    "mitchell starc": "Mitchell Starc",
    "tristan stubbs": "Tristan Stubbs",
    "jos buttler": "Jos Buttler",
    "glenn phillips": "Glenn Phillips",
    "mohammad siraj": "Mohammad Siraj",
    "prasidh krishna": "Prasidh Krishna",
    "sai sudharsan": "Sai Sudharsan",
    "shahrukh khan": "Shahrukh Khan",
    "ajinkya rahane": "Ajinkya Rahane",
    "angkrish raghuvanshi": "Angkrish Raghuvanshi",
    "rovman powell": "Rovman Powell",
    "sunil narine": "Sunil Narine",
    "vaibhav arora": "Vaibhav Arora",
    "varun chakaravarthy": "Varun Chakaravarthy",
    "aiden markram": "Aiden Markram",
    "manimaran siddharth": "Manimaran Siddharth",
    "matthew breetzke": "Matthew Breetzke",
    "mitchell marsh": "Mitchell Marsh",
    "nicholas pooran": "Nicholas Pooran",
    "rishabh pant": "Rishabh Pant",
    "deepak chahar": "Deepak Chahar",
    "hardik pandya": "Hardik Pandya",
    "jasprit bumrah": "Jasprit Bumrah",
    "mayank markande": "Mayank Markande",
    "mitchell santner": "Mitchell Santner",
    "raj angad bawa": "Raj Angad Bawa",
    "ryan rickelton": "Ryan Rickelton",
    "sherfane rutherford": "Sherfane Rutherford",
    "suryakumar yadav": "Suryakumar Yadav",
    "trent boult": "Trent Boult",
    "will jacks": "Will Jacks",
    "lockie ferguson": "Lockie Ferguson",
    "marco jansen": "Marco Jansen",
    "marcus stoinis": "Marcus Stoinis",
    "mitch owen": "Mitch Owen",
    "nehal wadhera": "Nehal Wadhera",
    "shreyas iyer": "Shreyas Iyer",
    "vyshak vijaykumar": "Vyshak Vijaykumar",
    "xavier bartlett": "Xavier Bartlett",
    "yuzvendra chahal": "Yuzvendra Chahal",
    "devdutt padikkal": "Devdutt Padikkal",
    "jacob bethell": "Jacob Bethell",
    "josh hazlewood": "Josh Hazlewood",
    "krunal pandya": "Krunal Pandya",
    "nuwan thushara": "Nuwan Thushara",
    "phil salt": "Phil Salt",
    "rajat patidar": "Rajat Patidar",
    "romario shepherd": "Romario Shepherd",
    "tim david": "Tim David",
    "virat kohli": "Virat Kohli",
    "eshan malinga": "Eshan Malinga",
    "heinrich klaasen": "Heinrich Klaasen",
    "jaydev unadkat": "Jaydev Unadkat",
    "nitish kumar reddy": "Nitish Kumar Reddy",
    "pat cummins": "Pat Cummins",
    "travis head": "Travis Head",
    "ravi bishnoi": "Ravi Bishnoi",
    "rahul chahar": "Rahul Chahar",
    "adam milne": "Adam Milne",
}


def canonical_player_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    norm = normalize_name(name)
    return DISPLAY_NAME_FIXES.get(norm, name)


def first_initial_key(name: str) -> str:
    norm = normalize_name(name)
    if not norm:
        return ""
    parts = norm.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0][0]} {' '.join(parts[1:])}"


def surname_key(name: str) -> str:
    norm = normalize_name(name)
    parts = norm.split()
    return parts[-1] if parts else ""


def price_increment(current_price: float) -> float:
    if current_price < 1.0:
        return 0.10
    if current_price < 2.0:
        return 0.20
    if current_price < 5.0:
        return 0.25
    return 0.50


def english_auction_price(valuations: list[float], reserve_price: float) -> float:
    price = round(reserve_price, 2)
    while True:
        next_price = round(price + price_increment(price), 2)
        active = sum(v + 1e-9 >= next_price for v in valuations)
        if active >= 2:
            price = next_price
        else:
            return round(price, 2)


def make_unique_header(row: pd.Series) -> list[str]:
    seen: dict[str, int] = {}
    cols = []
    for i, value in enumerate(row):
        name = str(value).replace("\n", " ").strip() if pd.notna(value) and str(value).strip() else f"col_{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        cols.append(name)
    return cols


def merge_nested_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_nested_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_context_payload(context_file: str | None) -> dict[str, Any]:
    if not context_file:
        return {}
    return json.loads(Path(context_file).read_text())


def season_context_block(payload: dict[str, Any], season: str) -> dict[str, Any]:
    seasons = payload.get("seasons")
    if isinstance(seasons, dict):
        return seasons.get(str(season), {})
    legacy = payload.get(str(season), {})
    if isinstance(legacy, dict):
        return {"teams": legacy}
    return {}


def season_defaults(payload: dict[str, Any], season: str) -> dict[str, Any]:
    return season_context_block(payload, season).get("auction_format", {})


def resolve_team_configs(season: str = "2026", context_file: str | None = None) -> dict[str, dict[str, Any]]:
    configs = copy.deepcopy(BASE_TEAM_CONFIGS)
    payload = load_context_payload(context_file)
    format_defaults = merge_nested_dict(DEFAULT_AUCTION_FORMAT, season_defaults(payload, season))
    for team_code, config in configs.items():
        configs[team_code] = merge_nested_dict(format_defaults, config)
    if context_file:
        season_overrides = season_context_block(payload, season).get("teams", {})
        for team_code, override in season_overrides.items():
            base = configs.get(team_code, copy.deepcopy(format_defaults))
            configs[team_code] = merge_nested_dict(base, override)
    return configs


def resolve_auction_file(
    season: str = "2026",
    auction_file: str | None = None,
    context_file: str | None = None,
) -> Path:
    if auction_file:
        return Path(auction_file)
    season_file = season_context_block(load_context_payload(context_file), season).get("auction_file")
    if season_file:
        return Path(season_file)
    return DEFAULT_AUCTION_FILES.get(str(season), DEFAULT_AUCTION_FILES["2026"])


def resolve_sold_file(
    season: str = "2026",
    sold_file: str | None = None,
    context_file: str | None = None,
) -> Path:
    if sold_file:
        return Path(sold_file)
    season_file = season_context_block(load_context_payload(context_file), season).get("sold_file")
    if season_file:
        return Path(season_file)
    return DEFAULT_SOLD_FILES.get(str(season), DEFAULT_SOLD_FILES["2026"])


def load_auction_pool(
    season: str = "2026",
    auction_file: str | None = None,
    context_file: str | None = None,
) -> pd.DataFrame:
    raw = pd.read_excel(resolve_auction_file(season, auction_file, context_file), header=None)
    cols = make_unique_header(raw.iloc[1])
    df = raw.iloc[2:].copy()
    df.columns = cols
    df["set_no"] = pd.to_numeric(df["Set No."], errors="coerce")
    df = df[df["set_no"].notna()].copy()
    df["set_no"] = df["set_no"].astype(int)
    df["list_no"] = pd.to_numeric(df["List Sr. No."], errors="coerce")
    df["reserve_price"] = pd.to_numeric(df["Reserve Price Rs Lakh"], errors="coerce") / 100.0
    df["player_name"] = (df["First Name"].fillna("") + " " + df["Surname"].fillna("")).str.strip()
    df["player_norm"] = df["player_name"].map(normalize_name)
    df["name_key"] = df["player_name"].map(first_initial_key)
    df["surname_key"] = df["player_name"].map(surname_key)
    df["is_overseas"] = df["Country"].fillna("India").ne("India")
    df["specialism_clean"] = df["Specialism"].fillna("").str.upper().str.strip()
    df["bat_style"] = df["col_10"].fillna("").astype(str).str.upper().str.strip()
    df["bowl_style"] = df["col_11"].fillna("").astype(str).str.upper().str.strip()
    df["t20_caps"] = pd.to_numeric(df["T20 caps"], errors="coerce").fillna(0)
    df["ipl_matches"] = pd.to_numeric(df["IPL"], errors="coerce").fillna(0)
    df["prev_ipl_2025"] = pd.to_numeric(df["2025 IPL"], errors="coerce").fillna(0)
    df["capped_flag"] = df["C/U/A"].fillna("").astype(str).str.contains("Capped", case=False)
    set_col = "2026 Set" if "2026 Set" in df.columns else next((col for col in df.columns if "Set" in str(col)), "2026 Set")
    df["set_code"] = df[set_col].astype(str).str.strip()
    df["role_bucket"] = df.apply(classify_role_bucket, axis=1)
    return df.sort_values(["set_no", "list_no"]).reset_index(drop=True)


def randomize_within_set_order(players: pd.DataFrame, seed: int | None = None) -> pd.DataFrame:
    rng = random.Random(seed)
    pieces: list[pd.DataFrame] = []
    for _, group in players.groupby("set_no", sort=True):
        rows = list(group.to_dict("records"))
        rng.shuffle(rows)
        pieces.append(pd.DataFrame(rows))
    randomized = pd.concat(pieces, ignore_index=True)
    return randomized.reset_index(drop=True)


def classify_role_bucket(row: pd.Series) -> str:
    specialism = row["specialism_clean"]
    set_code = row["set_code"]
    bowl_style = row["bowl_style"]
    is_overseas = bool(row["is_overseas"])

    if specialism == "WICKETKEEPER":
        return "wicketkeeper"
    if specialism == "BATTER":
        if set_code.startswith("BA") and row["bat_style"] == "LHB":
            return "top_order_bat"
        if set_code.startswith("BA"):
            return "middle_bat"
        return "domestic_bat_depth"
    if specialism == "ALL-ROUNDER":
        if "SPIN" in bowl_style or "ORTHODOX" in bowl_style or "UNORTHODOX" in bowl_style:
            return "spin_all_rounder"
        return "seam_all_rounder"
    if specialism == "BOWLER":
        spin_terms = ["LEG SPIN", "OFF SPIN", "ORTHODOX", "UNORTHODOX", "SLOW"]
        is_spin = any(term in bowl_style for term in spin_terms)
        if is_spin and not is_overseas:
            return "indian_spin"
        if is_spin:
            return "spin_bowler"
        if is_overseas:
            return "overseas_pace"
        return "domestic_pace"
    return "domestic_bat_depth"


def build_phase_index() -> dict[str, dict[str, float]]:
    files = [
        (DATA_DIR / "powerplay_batting_all_time.csv", "batter", "pp_bat"),
        (DATA_DIR / "middle_batting_all_time.csv", "batter", "mid_bat"),
        (DATA_DIR / "death_batting_all_time.csv", "batter", "death_bat"),
        (DATA_DIR / "powerplay_bowling_all_time.csv", "bowler", "pp_bowl"),
        (DATA_DIR / "middle_bowling_all_time.csv", "bowler", "mid_bowl"),
        (DATA_DIR / "death_bowling_all_time.csv", "bowler", "death_bowl"),
    ]
    index: dict[str, dict[str, float]] = {}

    for path, name_col, label in files:
        frame = pd.read_csv(path)
        score_col = "impact_score"
        max_score = frame[score_col].max()
        for _, row in frame.iterrows():
            raw_name = row[name_col]
            keys = {
                normalize_name(raw_name),
                first_initial_key(raw_name),
                surname_key(raw_name),
            }
            value = float(row[score_col]) / max_score if max_score else 0.0
            for key in keys:
                if not key:
                    continue
                bucket = index.setdefault(key, {})
                bucket[label] = max(value, bucket.get(label, 0.0))
    return index


def add_player_valuation_columns(
    players: pd.DataFrame,
    season: str = "2026",
    sold_file: str | None = None,
    context_file: str | None = None,
) -> pd.DataFrame:
    phase_index = build_phase_index()
    sold_names = set(
        pd.read_csv(resolve_sold_file(season, sold_file, context_file))["Name"]
        .astype(str)
        .map(normalize_name)
        .tolist()
    )

    quality_scores = []
    ceiling_values = []

    for _, row in players.iterrows():
        phase_scores = (
            phase_index.get(row["player_norm"])
            or phase_index.get(row["name_key"])
            or phase_index.get(row["surname_key"])
            or {}
        )
        batting_signal = max(
            phase_scores.get("pp_bat", 0.0),
            phase_scores.get("mid_bat", 0.0),
            phase_scores.get("death_bat", 0.0),
        )
        bowling_signal = max(
            phase_scores.get("pp_bowl", 0.0),
            phase_scores.get("mid_bowl", 0.0),
            phase_scores.get("death_bowl", 0.0),
        )
        all_round_signal = (batting_signal + bowling_signal) / 2.0

        prior = (
            0.16 * min(row["ipl_matches"], 120) / 120.0
            + 0.12 * min(row["t20_caps"], 100) / 100.0
            + 0.10 * min(row["prev_ipl_2025"], 14) / 14.0
            + 0.10 * float(row["capped_flag"])
        )

        if row["specialism_clean"] == "BATTER":
            quality = 0.58 * batting_signal + prior
        elif row["specialism_clean"] == "WICKETKEEPER":
            quality = 0.50 * batting_signal + 0.08 + prior
        elif row["specialism_clean"] == "BOWLER":
            quality = 0.62 * bowling_signal + prior
        else:
            quality = 0.36 * batting_signal + 0.36 * bowling_signal + 0.08 + prior

        quality += 0.08 if row["player_norm"] in sold_names else -0.03
        quality = max(0.05, min(1.0, quality))

        reserve = float(row["reserve_price"])
        if row["role_bucket"] == "indian_spin":
            multiplier = 3.35
        elif row["role_bucket"] == "overseas_pace":
            multiplier = 2.45
        elif row["role_bucket"] in {"spin_bowler", "domestic_pace"}:
            multiplier = 2.05
        elif row["role_bucket"] in {"wicketkeeper", "seam_all_rounder", "spin_all_rounder"}:
            multiplier = 2.15
        else:
            multiplier = 1.85

        ceiling = max(reserve, reserve + multiplier * quality * (1.0 + reserve / 3.5))
        quality_scores.append(round(quality, 4))
        ceiling_values.append(round(ceiling, 2))

    enriched = players.copy()
    enriched["quality_score"] = quality_scores
    enriched["base_ceiling"] = ceiling_values
    return enriched


def build_team_states(team_configs: dict[str, dict[str, Any]]) -> dict[str, TeamState]:
    states = {}
    max_purse = max(config["purse"] for config in team_configs.values())
    for code, config in team_configs.items():
        squad_size = int(config.get("squad_size", DEFAULT_AUCTION_FORMAT["squad_size"]))
        overseas_limit = int(config.get("overseas_limit", DEFAULT_AUCTION_FORMAT["overseas_limit"]))
        max_open_slots = max(0, squad_size - config["retained"])
        max_buys = min(config.get("max_buys", max_open_slots), max_open_slots)
        min_buys = min(config.get("min_buys", max_open_slots), max_buys)
        purse_scale = config["purse"] / max_purse
        slot_pressure = max_open_slots / 13.0
        overseas_flex = max(0, overseas_limit - config["overseas_retained"]) / max(1.0, overseas_limit - 2.0)
        aggression = round(0.82 + 0.30 * purse_scale + 0.18 * slot_pressure + 0.08 * overseas_flex, 3)
        states[code] = TeamState(
            code=code,
            purse=config["purse"],
            spent=config["spent"],
            retained=config["retained"],
            overseas_retained=config["overseas_retained"],
            squad_size=squad_size,
            overseas_limit=overseas_limit,
            aggression=aggression,
            role_needs=config["role_needs"].copy(),
            role_caps=config.get("role_caps", {}).copy(),
            focus_strategy=copy.deepcopy(config.get("focus_strategy", {})),
            max_buys=max_buys,
            min_buys=min_buys,
        )
    return states


def role_need_weight(team: TeamState, role: str) -> float:
    base = team.role_needs.get(role, 0.0)
    for alt_role, weight in ROLE_NEED_EQUIVALENTS.get(role, {}).items():
        base = max(base, team.role_needs.get(alt_role, 0.0) * weight)
    filled = team.role_counts.get(role, 0)
    if filled <= 0:
        return base
    return max(0.05, base * (0.42 ** filled))


def future_role_supply(players: pd.DataFrame, current_index: int, role: str) -> int:
    tail = players.iloc[current_index + 1 :]
    return int((tail["role_bucket"] == role).sum())


def reserve_buffer(team: TeamState) -> float:
    remaining_after_current = max(0, team.min_buys - len(team.purchases) - 1)
    return round(0.30 * remaining_after_current, 2)


def future_priority_target_exists(
    focus_team: str,
    players: pd.DataFrame,
    current_index: int,
    role: str,
    current_player_norm: str,
) -> bool:
    target = TEAM_PRIORITY_TARGETS.get(focus_team, {}).get(role)
    if not target or current_player_norm == target:
        return False
    tail = players.iloc[current_index + 1 :]
    remaining = tail[(tail["role_bucket"] == role) & (tail["player_norm"] == target)]
    return not remaining.empty


def feasible_bid_cap(team: TeamState, player: pd.Series) -> float:
    if team.buys_left <= 0:
        return -1.0
    if player["is_overseas"] and team.overseas_slots_left <= 0:
        return -1.0

    cap = team.purse - reserve_buffer(team)
    role_cap = team.role_caps.get(player["role_bucket"])
    if role_cap is not None:
        cap = min(cap, role_cap)
    return round(cap, 2)


def team_player_valuation(
    team: TeamState,
    player: pd.Series,
    current_index: int,
    auction_pool: pd.DataFrame,
) -> float:
    role = player["role_bucket"]
    need = role_need_weight(team, role)
    if need <= 0:
        return -1.0

    cap = feasible_bid_cap(team, player)
    if cap < player["reserve_price"]:
        return -1.0

    scarcity_left = future_role_supply(auction_pool, current_index, role)
    scarcity_boost = 1.0 + min(0.35, 1.6 / max(scarcity_left, 5))
    quality = float(player["quality_score"])
    reserve = float(player["reserve_price"])
    base = float(player["base_ceiling"])

    value = base * team.aggression
    value *= 0.88 + min(0.35, team.auction_power / 4.0)
    value *= 0.75 + need
    value *= scarcity_boost

    if role == "indian_spin":
        value *= 0.92 + 0.55 * need
        if scarcity_left <= 8 and need >= 0.15:
            value *= 1.08
    elif role == "spin_bowler" and not player["is_overseas"]:
        value *= 1.08

    if player["is_overseas"] and team.overseas_slots_left == 1:
        value *= 1.15 if role == "overseas_pace" else 0.72

    if team.focus_strategy:
        strategy = team.focus_strategy
        singleton_roles = set(strategy.get("singleton_roles", []))
        core_roles = set(strategy.get("core_roles", []))
        non_core_hold_until_set = int(strategy.get("non_core_hold_until_set", 0))
        late_stage_set = int(strategy.get("late_stage_set", 30))
        late_stage_min_quality = float(strategy.get("late_stage_min_quality", 0.24))
        premium_reserve_roles = set(strategy.get("premium_reserve_roles", []))
        premium_reserve_discount = float(strategy.get("premium_reserve_discount", 1.0))

        if role in singleton_roles and team.role_counts.get(role, 0) >= 1:
            return -1.0
        core_filled = core_roles.issubset(team.role_counts.keys()) if core_roles else True
        if not core_filled and role not in core_roles and player["set_no"] < non_core_hold_until_set:
            return -1.0
        if future_priority_target_exists(team.code, auction_pool, current_index, role, player["player_norm"]) and role in core_roles:
            if player["reserve_price"] >= float(strategy.get("priority_target_reserve_floor", 1.5)):
                return -1.0
        if role == "indian_spin":
            value *= 1.30
        elif role == "overseas_pace":
            value *= 1.18
        elif role in {"domestic_pace", "domestic_all_rounder", "domestic_bat_depth"}:
            value *= 0.92
        if player["player_norm"] in TEAM_PRIORITY_TARGETS.get(team.code, {}).values():
            value *= float(strategy.get("priority_target_bonus", 1.0))

        late_stage = player["set_no"] >= late_stage_set
        if late_stage and core_filled and quality < late_stage_min_quality:
            return -1.0
        if reserve >= 2.0 and role not in premium_reserve_roles:
            value *= premium_reserve_discount
        if role == "overseas_pace" and player["set_no"] <= int(strategy.get("overseas_very_early_set_cutoff", -1)) and reserve >= 2.0:
            value *= float(strategy.get("overseas_very_early_discount", 1.0))
        if role == "overseas_pace" and player["set_no"] < int(strategy.get("overseas_early_set_cutoff", -1)):
            value *= float(strategy.get("overseas_early_discount", 1.0))
        if role == "overseas_pace" and "RIGHT ARM FAST" in player["bowl_style"]:
            value *= float(strategy.get("overseas_right_arm_fast_bonus", 1.0))
        if role == "overseas_pace" and "LEFT ARM" in player["bowl_style"]:
            value *= float(strategy.get("overseas_left_arm_discount", 1.0))
        if strategy.get("domestic_bat_requires_spin", False) and role == "domestic_bat_depth" and team.role_counts.get("indian_spin", 0) == 0:
            value *= 0.80

    if quality < 0.18 and reserve > 0.30:
        value *= 0.82

    value = min(value, cap)
    if value < player["reserve_price"]:
        return -1.0
    return round(value, 2)


def run_auction_simulation(
    focus_team: str = "RR",
    season: str = "2026",
    context_file: str | None = None,
    auction_file: str | None = None,
    sold_file: str | None = None,
    randomize_within_set: bool = False,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, TeamState]]:
    team_configs = resolve_team_configs(season=season, context_file=context_file)
    return run_auction_with_team_configs(
        team_configs=team_configs,
        focus_team=focus_team,
        season=season,
        context_file=context_file,
        auction_file=auction_file,
        sold_file=sold_file,
        randomize_within_set=randomize_within_set,
        seed=seed,
    )


def run_auction_with_team_configs(
    team_configs: dict[str, dict[str, Any]],
    focus_team: str = "RR",
    season: str = "2026",
    context_file: str | None = None,
    auction_file: str | None = None,
    sold_file: str | None = None,
    randomize_within_set: bool = False,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, TeamState]]:
    auction_pool = add_player_valuation_columns(
        load_auction_pool(season=season, auction_file=auction_file, context_file=context_file),
        season=season,
        sold_file=sold_file,
        context_file=context_file,
    )
    if randomize_within_set:
        auction_pool = randomize_within_set_order(auction_pool, seed=seed)
    teams = build_team_states(team_configs)
    events: list[dict[str, Any]] = []

    for idx, player in auction_pool.iterrows():
        valuations = {}
        focus_pre_bid_cap = team_player_valuation(teams[focus_team], player, idx, auction_pool)
        for code, team in teams.items():
            val = focus_pre_bid_cap if code == focus_team else team_player_valuation(team, player, idx, auction_pool)
            if val >= player["reserve_price"]:
                valuations[code] = val

        if not valuations:
            events.append(
                {
                    "set_no": player["set_no"],
                    "player_name": player["player_name"],
                    "role_bucket": player["role_bucket"],
                    "reserve_price": player["reserve_price"],
                    "winner": None,
                    "final_price": None,
                    "runner_up": None,
                    "season": season,
                    "focus_team": focus_team,
                    "simulation_seed": seed,
                    "focus_team_bid_cap": focus_pre_bid_cap,
                    "quality_score": player["quality_score"],
                }
            )
            continue

        ordered = sorted(valuations.items(), key=lambda item: (item[1], teams[item[0]].purse), reverse=True)
        winner_code, top_value = ordered[0]
        valuation_list = [value for _, value in ordered]
        final_price = english_auction_price(valuation_list, float(player["reserve_price"]))
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

        events.append(
            {
                "set_no": int(player["set_no"]),
                "player_name": player["player_name"],
                "role_bucket": player["role_bucket"],
                "reserve_price": round(float(player["reserve_price"]), 2),
                "winner": winner_code,
                "final_price": round(final_price, 2),
                "runner_up": ordered[1][0] if len(ordered) > 1 else None,
                "season": season,
                "focus_team": focus_team,
                "simulation_seed": seed,
                "focus_team_bid_cap": focus_pre_bid_cap,
                "quality_score": float(player["quality_score"]),
            }
        )

    events_df = pd.DataFrame(events)
    focus_df = events_df[events_df["winner"] == focus_team].copy()
    return events_df, focus_df, teams


def compare_team_to_actual(team_code: str, team_df: pd.DataFrame) -> pd.DataFrame:
    simulated = set(team_df["player_name"].tolist())
    rows = []
    for actual_name, note in ACTUAL_TEAM_PURCHASES.get(team_code, {}).items():
        rows.append(
            {
                "actual_player": actual_name,
                "actual_note": note,
                "simulated": actual_name in simulated,
            }
        )
    return pd.DataFrame(rows)


def extract_team_buys(events_df: pd.DataFrame, team_code: str) -> pd.DataFrame:
    if events_df.empty or "winner" not in events_df.columns:
        return pd.DataFrame(columns=events_df.columns)
    return events_df[events_df["winner"] == team_code].copy()


def summarize_focus_simulations(results: list[pd.DataFrame], focus_team: str) -> pd.DataFrame:
    purchase_counts: dict[str, int] = {}
    purchase_prices: dict[str, list[float]] = {}
    spend_rows = []
    for run_id, focus_df in enumerate(results, start=1):
        total_spend = float(focus_df["final_price"].fillna(0).sum()) if not focus_df.empty else 0.0
        spend_rows.append({"run_id": run_id, "focus_team": focus_team, "total_spend": round(total_spend, 2)})
        for _, row in focus_df.iterrows():
            player_name = row["player_name"]
            purchase_counts[player_name] = purchase_counts.get(player_name, 0) + 1
            purchase_prices.setdefault(player_name, []).append(float(row["final_price"]))

    summary = [
        {
            "player_name": player,
            "times_bought": count,
            "share_of_runs": round(count / max(1, len(results)), 3),
            "avg_price_when_bought": round(sum(purchase_prices.get(player, [])) / max(1, len(purchase_prices.get(player, []))), 2),
        }
        for player, count in sorted(purchase_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return pd.DataFrame(summary), pd.DataFrame(spend_rows)


def build_scenario_template(
    season: str,
    base_team_configs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    configs = copy.deepcopy(base_team_configs or BASE_TEAM_CONFIGS)
    teams_payload: dict[str, Any] = {}
    for team_code, config in sorted(configs.items()):
        teams_payload[team_code] = {
            "name": config["name"],
            "purse": config["purse"],
            "spent": config["spent"],
            "retained": config["retained"],
            "overseas_retained": config["overseas_retained"],
            "retained_players": config["retained_players"],
            "max_buys": config.get("max_buys"),
            "min_buys": config.get("min_buys"),
            "role_needs": config.get("role_needs", {}),
            "role_caps": config.get("role_caps", {}),
            "focus_strategy": config.get("focus_strategy", {}),
        }
    return {
        "seasons": {
            str(season): {
                "auction_format": copy.deepcopy(DEFAULT_AUCTION_FORMAT),
                "auction_file": f"/path/to/ipl_auction_{season}_full.xlsx",
                "sold_file": f"/path/to/IPL_Auction_{season}_Sold_Player.csv",
                "teams": teams_payload,
            }
        }
    }


def write_scenario_template(output_path: str, season: str) -> Path:
    payload = build_scenario_template(season)
    path = Path(output_path)
    path.write_text(json.dumps(payload, indent=2))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate an IPL English auction for a focus franchise.")
    parser.add_argument("--team", default="RR", choices=sorted(BASE_TEAM_CONFIGS.keys()))
    parser.add_argument("--season", default="2026", help="Season label, e.g. 2026, 2027, 2028")
    parser.add_argument("--context-file", help="JSON file with team-context overrides for future seasons")
    parser.add_argument("--auction-file", help="Auction workbook path for the chosen season")
    parser.add_argument("--sold-file", help="Sold-player CSV path for the chosen season")
    parser.add_argument("--keep-listed-order", action="store_true", help="Use workbook order within each set instead of randomizing")
    parser.add_argument("--seed", type=int, help="Seed for within-set randomization")
    parser.add_argument("--iterations", type=int, default=1, help="Number of repeated simulations to run")
    parser.add_argument("--write-scenario-template", help="Write a reusable future-season scenario JSON and exit")
    args = parser.parse_args()

    focus_team = args.team
    season = str(args.season)
    randomize_within_set = not args.keep_listed_order
    if args.write_scenario_template:
        output_path = write_scenario_template(args.write_scenario_template, season)
        print(f"Wrote scenario template for season {season}:")
        print(output_path)
        return

    out_dir = DATA_DIR
    slug = focus_team.lower()
    if args.iterations <= 1:
        events_df, focus_df, teams = run_auction_simulation(
            focus_team=focus_team,
            season=season,
            context_file=args.context_file,
            auction_file=args.auction_file,
            sold_file=args.sold_file,
            randomize_within_set=randomize_within_set,
            seed=args.seed,
        )
        focus_state = teams[focus_team]
        events_path = out_dir / f"auction_simulation_{season}_events_{slug}.csv"
        focus_path = out_dir / f"{slug}_auction_simulated_buys_{season}.csv"
        compare_path = out_dir / f"{slug}_actual_vs_simulated_{season}.csv"

        events_df.to_csv(events_path, index=False)
        focus_df.to_csv(focus_path, index=False)
        compare_df = compare_team_to_actual(focus_team, focus_df)
        if not compare_df.empty:
            compare_df.to_csv(compare_path, index=False)

        if season == "2026" and focus_team == "RR":
            events_df.to_csv(out_dir / "auction_simulation_2026_events.csv", index=False)
            focus_df.to_csv(out_dir / "rr_auction_simulated_buys.csv", index=False)
            if not compare_df.empty:
                compare_df.to_csv(out_dir / "rr_actual_vs_simulated.csv", index=False)

        print("Valid auction sets used:", sorted(events_df["set_no"].dropna().unique())[:5], "...", sorted(events_df["set_no"].dropna().unique())[-5:])
        print(f"Within-set order randomized: {randomize_within_set}")
        print(f"{focus_team} simulated purchases:")
        if focus_df.empty:
            print("  None")
        else:
            print(focus_df[["set_no", "player_name", "role_bucket", "final_price", "runner_up"]].to_string(index=False))
        print(f"{focus_team} purse left: {focus_state.purse:.2f} Cr")
        print(f"{focus_team} overseas slots left: {focus_state.overseas_slots_left}")
        print("Saved:")
        print(events_path)
        print(focus_path)
        if not compare_df.empty:
            print(compare_path)
        return

    all_events = []
    all_focus = []
    focus_runs = []
    base_seed = args.seed if args.seed is not None else 0
    for iteration in range(args.iterations):
        iteration_seed = base_seed + iteration if randomize_within_set else None
        events_df, focus_df, _ = run_auction_simulation(
            focus_team=focus_team,
            season=season,
            context_file=args.context_file,
            auction_file=args.auction_file,
            sold_file=args.sold_file,
            randomize_within_set=randomize_within_set,
            seed=iteration_seed,
        )
        events_copy = events_df.copy()
        focus_copy = focus_df.copy()
        events_copy["run_id"] = iteration + 1
        focus_copy["run_id"] = iteration + 1
        all_events.append(events_copy)
        all_focus.append(focus_copy)
        focus_runs.append(focus_copy)

    events_all_df = pd.concat(all_events, ignore_index=True)
    focus_all_df = pd.concat(all_focus, ignore_index=True) if all_focus else pd.DataFrame()
    purchase_summary_df, spend_summary_df = summarize_focus_simulations(focus_runs, focus_team)

    events_path = out_dir / f"auction_simulation_{season}_events_{slug}_mc.csv"
    focus_path = out_dir / f"{slug}_auction_simulated_buys_{season}_mc.csv"
    summary_path = out_dir / f"{slug}_auction_purchase_summary_{season}_mc.csv"
    spend_path = out_dir / f"{slug}_auction_spend_summary_{season}_mc.csv"
    events_all_df.to_csv(events_path, index=False)
    focus_all_df.to_csv(focus_path, index=False)
    purchase_summary_df.to_csv(summary_path, index=False)
    spend_summary_df.to_csv(spend_path, index=False)

    print(f"Ran {args.iterations} simulations for {focus_team}.")
    print(f"Within-set order randomized: {randomize_within_set}")
    if not purchase_summary_df.empty:
        print(purchase_summary_df.head(10).to_string(index=False))
    print("Saved:")
    print(events_path)
    print(focus_path)
    print(summary_path)
    print(spend_path)


if __name__ == "__main__":
    main()
