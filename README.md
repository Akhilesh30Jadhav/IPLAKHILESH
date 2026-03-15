# IPL Auction Intelligence League Hub

This project studies IPL team-building through the combination of ball-by-ball performance measurement, phase-specific player evaluation, and a sequential auction model calibrated to the IPL auction format.

At a high level, the project does three things:

1. builds phase-based batting and bowling measures from IPL ball-by-ball data
2. converts those signals into player quality, impact, and wins-added style metrics
3. uses those signals inside a set-wise English auction simulator with budget, roster, and overseas-slot constraints

The current dashboard turns those outputs into an interactive league-wide tool for auction strategy, player comparison, and batter-bowler matchup analysis.

## Project Structure

- [Code/A1_code.ipynb](/Users/piyushzaware/Documents/IPL_Data_Analysis/Code/A1_code.ipynb): original analysis notebook with the core data construction, phase rankings, impact measures, and wins-added proxy
- [Code/rr_auction_simulator.py](/Users/piyushzaware/Documents/IPL_Data_Analysis/Code/rr_auction_simulator.py): auction simulator and team calibration logic
- [Code/run_league_monte_carlo.py](/Users/piyushzaware/Documents/IPL_Data_Analysis/Code/run_league_monte_carlo.py): shared league Monte Carlo simulation runner
- [Dashboard/index.html](/Users/piyushzaware/Documents/IPL_Data_Analysis/Dashboard/index.html): main dashboard
- [Dashboard/server.py](/Users/piyushzaware/Documents/IPL_Data_Analysis/Dashboard/server.py): local web server and scenario API
- [Paper/rr_auction_paper.tex](/Users/piyushzaware/Documents/IPL_Data_Analysis/Paper/rr_auction_paper.tex): paper draft in LaTeX
- [Data/ipl_ball_by_ball.csv](/Users/piyushzaware/Documents/IPL_Data_Analysis/Data/ipl_ball_by_ball.csv): cleaned ball-by-ball dataset used throughout the project

## Data

The project is built from a cleaned IPL ball-by-ball sample covering matches from 2008 through 2025, together with 2026 auction inputs:

- match-level JSON archives in [Data/ipl_json](/Users/piyushzaware/Documents/IPL_Data_Analysis/Data/ipl_json)
- cleaned ball-by-ball table in [Data/ipl_ball_by_ball.csv](/Users/piyushzaware/Documents/IPL_Data_Analysis/Data/ipl_ball_by_ball.csv)
- auction workbook in [Data/ipl_auction_2026_full.xlsx](/Users/piyushzaware/Documents/IPL_Data_Analysis/Data/ipl_auction_2026_full.xlsx)
- sold-player file in [Data/IPL_Auction_2026_Sold_Player.csv](/Users/piyushzaware/Documents/IPL_Data_Analysis/Data/IPL_Auction_2026_Sold_Player.csv)

The core cricket unit is the delivery. Each delivery is labeled with the batter, bowler, innings state, phase, and outcome variables required for batting, bowling, and matchup analysis.

## Method

### 1. Phase segmentation

Every innings is split into three standard T20 phases:

- powerplay
- middle overs
- death overs

This matters because player value in T20 cricket is highly phase-dependent. A batter who dominates at the death is not the same asset as a batter who anchors through the middle, and a bowler who controls the powerplay is not interchangeable with a death specialist.

### 2. Batting measurement

For each batter and phase, the notebook constructs:

- runs
- balls
- strike rate

The raw phase strike rate is then shrunk toward the league mean using a Bayesian adjustment:

$$
sr^{bayes}_{i,p} = \frac{B_{i,p}}{B_{i,p}+k}\,sr_{i,p} + \frac{k}{B_{i,p}+k}\,\bar{sr}_{p}
$$

where:

- $i$ is the batter
- $p$ is the phase
- $B_{i,p}$ is balls faced in that phase
- $sr_{i,p}$ is the raw strike rate
- $\bar{sr}_{p}$ is the league phase mean
- $k$ is the shrinkage constant

The batting impact score is then:

$$
Impact^{bat}_{i,p} = sr^{bayes}_{i,p} \times B_{i,p}
$$

This rewards both quality and credible sample size. A player cannot rank highly on a tiny sample alone.

### 3. Bowling measurement

For each bowler and phase, the notebook constructs:

- runs conceded
- balls bowled
- wickets
- economy rate

The phase economy is also Bayesian-shrunk:

$$
econ^{bayes}_{i,p} = \frac{B_{i,p}}{B_{i,p}+k}\,econ_{i,p} + \frac{k}{B_{i,p}+k}\,\bar{econ}_{p}
$$

Bowling impact is then constructed as:

$$
Impact^{bowl}_{i,p} = (\bar{econ}_{p} - econ^{bayes}_{i,p}) \times B_{i,p} + \omega \times W_{i,p}
$$

where:

- $\bar{econ}_{p}$ is league phase economy
- $W_{i,p}$ is wickets in that phase
- $\omega$ is the wicket weight

This gives credit to run suppression and wicket-taking rather than using economy alone.

### 4. Player quality construction

The auction model does not use raw phase impact alone. It constructs a broader player quality score by combining:

- phase batting impact
- phase bowling impact
- experience priors
- public market priors

The simulator first builds batting and bowling signals from the strongest available phase-specific impacts. Then it adds priors for:

- IPL experience
- broader T20 experience
- recent IPL usage
- capped or uncapped status
- whether the player appears in the auction market as a sold player

Conceptually:

$$
q_i = f(\text{phase impact}_i, \text{experience}_i, \text{market prior}_i)
$$

Role-specific weights are then applied differently for batters, bowlers, wicketkeepers, and all-rounders inside [Code/rr_auction_simulator.py](/Users/piyushzaware/Documents/IPL_Data_Analysis/Code/rr_auction_simulator.py).

### 5. Run value and wins-added proxy

The notebook sketches a fuller run-expectancy and win-probability framework, but the currently implemented version uses a tractable wins-added proxy.

At the ball level:

$$
run\_value_b = runs\_total_b - \overline{runs\_total}
$$

These ball-level values are then aggregated to the player level. For batters:

$$
RunsAdded_i = \sum_b run\_value_b
$$

and for bowlers, the sign is reversed when interpreting value saved.

Wins added is then approximated by:

$$
WinsAdded_i = \frac{RunsAdded_i}{15}
$$

using the notebook assumption that roughly 15 runs correspond to about 1 win.

This should be interpreted carefully:

- it is a wins-added style proxy
- it is not yet a full structural win-probability model
- it is most useful as a tractable ranking and comparison device inside the dashboard

### 6. Auction model

The auction side of the project models the IPL auction as a sequential English auction with roster and budget constraints.

The main ingredients are:

- players come up set by set
- order is randomized within each set
- teams bid openly until price exceeds willingness to pay
- bid increments rise with price level
- each team is constrained by purse, roster slots, and overseas slots

The key auction-theoretic intuition is:

$$
P_i \approx \text{second-highest valuation} + \text{bid increment}
$$

For team $t$, player $i$, and auction state $s$, the model uses a state-dependent valuation:

$$
v_{t,i,s} = q_i + fit_{t,i,s} + scarcity_{i,s} - \lambda^p_{t,s} - \lambda^o_{t,s} - \lambda^r_{t,s}
$$

where:

- $q_i$ is player quality
- $fit_{t,i,s}$ captures role fit for the team
- $scarcity_{i,s}$ captures thin market supply
- $\lambda^p_{t,s}$ is the shadow cost of purse
- $\lambda^o_{t,s}$ is the shadow cost of an overseas slot
- $\lambda^r_{t,s}$ is the shadow cost of a roster spot

A team remains active in bidding while:

$$
current\_price + increment \leq walkaway_{t,i,s}
$$

with:

$$
walkaway_{t,i,s} = \min(v_{t,i,s}, feasible\ budget\ cap_{t,s})
$$

The simulator therefore does not treat player values as fixed. The same player can have a different walk-away price depending on:

- purse left
- overseas slots left
- open squad slots
- already-filled roles
- substitutes still to come later in the auction

### 7. Team calibration

Team priorities are not chosen by eyeballing the best player available. They are calibrated from the retained squad.

The logic is:

$$
Priority(role) = \text{best auction addition in role} - \text{best internal replacement in role}
$$

and then adjusted for:

- scarcity of substitutes
- purse constraints
- overseas-slot scarcity

This is what allows the same model to be used for Rajasthan Royals, Chennai Super Kings, or any other IPL team under a different retention structure and budget.

### 8. General-equilibrium scenario builder

The dashboard scenario builder runs a shared-auction counterfactual rather than a one-team partial-equilibrium ranking.

That means:

- multiple teams can be edited before the run
- all teams bid in the same simulated auction
- player prices clear in the common market
- changing one team's priorities affects the opportunities available to the others

This is closer to a general-equilibrium auction environment than isolated target ranking.

## Dashboard

The dashboard is designed as a sports analytics and front-office decision-support tool.

It includes:

- phase studio for batting and bowling leaderboards
- skill radar and player comparison tools
- wins-added proxy views
- live batter-bowler matchup intelligence
- a multi-team scenario builder with shared-auction counterfactuals
- league-wide auction summary views

Run locally:

```bash
python Dashboard/server.py
```

Then open:

```text
http://127.0.0.1:8000
```

To rebuild the front-end data bundle:

```bash
python Dashboard/build_dashboard_data.py
```

## Reproducing the analysis

### Notebook workflow

The original phase analytics and wins-added proxy are developed in:

- [Code/A1_code.ipynb](/Users/piyushzaware/Documents/IPL_Data_Analysis/Code/A1_code.ipynb)

### Auction workflow

Representative and Monte Carlo auction outputs can be regenerated from:

```bash
python Code/run_league_monte_carlo.py
```

### Paper

The research-paper draft is in:

- [Paper/rr_auction_paper.tex](/Users/piyushzaware/Documents/IPL_Data_Analysis/Paper/rr_auction_paper.tex)

## Deployment

This repo includes:

- [render.yaml](/Users/piyushzaware/Documents/IPL_Data_Analysis/render.yaml)
- [requirements.txt](/Users/piyushzaware/Documents/IPL_Data_Analysis/requirements.txt)

so the dashboard can be deployed directly on Render.

## Current scope and limitations

- The wins-added measure is currently a tractable proxy rather than a full win-probability model.
- The auction model is reduced-form and calibrated, not a fully estimated structural auction model with latent private values.
- Team role needs are calibrated from retained cores and public information; they do not include proprietary scouting information.
- Matchup intelligence uses observed ball-by-ball evidence plus style metadata, so thin-sample contests should be interpreted with caution.

## Why this project exists

The underlying question is simple: how should an IPL team allocate scarce auction budget when player value is phase-specific, roles are scarce, and every decision depends on what other teams do?

This project is an attempt to answer that question with the language of cricket analytics, auction theory, and decision-making under constraints.
