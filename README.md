# IPL Cricket Analytics Dashboard

> Five data questions that reframe how we think about IPL strategy —  
> built as a BA/Analyst portfolio project.

**Dataset:** 283,678 deliveries · 1,193 matches · 18 seasons (2008–2025)  
**Live App:** [ipl-analytics-dashboard-ipl1808.streamlit.app](https://ipl-analytics-dashboard-ipl1808.streamlit.app)

---

## The Five Questions

| # | Question | Why It Matters |
|---|----------|----------------|
| Q1 | Does winning the toss actually win matches — and has this changed across IPL eras? | Tests whether teams optimise for the wrong KPI |
| Q2 | Which bowlers are most destructive in death overs (16–20), controlling for opposition quality? | Pressure performance — the metric that wins auctions |
| Q3 | Has the IPL become a batsman's game over time — and when exactly did the inflection point happen? | Structural shift in the game's run economy |
| Q4 | Which teams consistently outperform their expected runs based on batting lineup strength? | Proxy for coaching and strategy alpha |
| Q5 | Is there a home ground advantage in IPL — and which franchises exploit it most vs. least? | Controls for venue familiarity as a competitive edge |

---

## Lead Finding — The Toss Trap

Toss winners convert to match winners only **51.8% of the time** —
statistically indistinguishable from a coin flip. Yet IPL teams invest 
enormous strategic effort optimising for toss outcomes. The story 
sharpens when segmented by venue: dew-factor grounds (Chennai, Kolkata) 
show measurable toss advantage while neutral venues show none. Teams are 
over-indexing on a metric that explains very little outcome variance — 
the IPL's version of optimising the wrong KPI.

---

## Tech Stack

- **Python 3.11** — pandas, numpy  
- **Streamlit** — dashboard framework  
- **Plotly** — interactive charts  
- **Data** — IPL ball-by-ball dataset, 2008–2025 (Kaggle · chaitu20)

---

## Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/gautamraju18/ipl-analytics-dashboard.git
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
# Dataset: [Kaggle — chaitu20 IPL Dataset]
# (INSERT CORRECT KAGGLE URL HERE)
# Download deliveries.csv and matches.csv → place both in data/

# 5. Launch the dashboard
streamlit run app/app.py
```

> **Note:** `data/` is gitignored. Download the CSVs manually 
> and place them in `data/` before running locally.

---

## Author

**Angajala Gautam Raju**  
Final-year B.Tech CSE   
[LinkedIn](https://linkedin.com/in/gautamraju18) · 
[Live Dashboard](https://ipl-analytics-dashboard-ipl1808.streamlit.app)