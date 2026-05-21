# IPL Cricket Analytics Dashboard

> Five data questions that reframe how we think about IPL strategy — built as a BA/Analyst portfolio project.

## The Five Questions

| # | Question | Why It Matters |
|---|----------|----------------|
| Q1 | Does winning the toss actually win matches — and has this changed across IPL eras? | Tests whether teams optimise for the wrong KPI |
| Q2 | Which bowlers are most destructive in death overs (16–20), controlling for opposition quality? | Pressure performance — the metric that wins auctions |
| Q3 | Has the IPL become a batsman's game over time — and when exactly did the inflection point happen? | Structural shift in the game's run economy |
| Q4 | Which teams consistently outperform their expected runs based on batting lineup strength? | Proxy for coaching and strategy alpha |
| Q5 | Is there a home ground advantage in IPL — and which franchises exploit it most vs. least? | Controls for venue familiarity as a competitive edge |

## The Toss Trap (Lead Finding)

Toss win–match win correlation collapses when you control for venue and era. Teams spend enormous
effort optimising for a coin flip that explains very little outcome variance. But the story gets
interesting when you segment by venue: dew-factor grounds (Chennai, Kolkata) show measurable toss
advantage while others show none. Nuance is what analysts are paid for.

## Tech Stack

- **Python 3.11** — pandas, numpy
- **Streamlit** — dashboard framework
- **Plotly** — interactive charts
- **Data** — IPL ball-by-ball dataset, 2008–2024 (Kaggle)

## Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/ipl-analytics-dashboard.git
cd ipl-analytics-dashboard

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the data
# Go to: https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020
# Download deliveries.csv and matches.csv → place both in data/

# 5. Run EDA (Day 1 validation)
python notebooks/eda.py

# 6. Launch the dashboard
streamlit run app/app.py
```

## Data Source

Kaggle — [IPL Complete Dataset 2008–2024](https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020)
Two CSVs: `deliveries.csv` (ball-by-ball) + `matches.csv` (match metadata), joined on `match_id`.

> **Note:** `data/` is gitignored. Download the CSVs manually and place them in `data/` before running.

## Live Dashboard

[Streamlit App](link-here) ← *deploying Friday May 23, 2026*

## Author

**Angajala Gautam Raju**
Final-year B.Tech CSE | CGPA 8.17
[linkedin.com/in/gautamraju18](https://linkedin.com/in/gautamraju18)
