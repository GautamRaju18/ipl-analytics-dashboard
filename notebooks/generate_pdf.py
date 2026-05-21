"""
Generate 1-page Insights PDF for IPL Analytics Dashboard.
Run from repo root: python notebooks/generate_pdf.py
Output: outputs/ipl_insights.pdf
Requires: fpdf2  (pip install fpdf2)
"""

import sys, os
sys.path.insert(0, "notebooks")
from config import load_clean

os.makedirs("outputs", exist_ok=True)

try:
    from fpdf import FPDF
except ImportError:
    print("ERROR: fpdf2 not installed. Run: pip install fpdf2")
    sys.exit(1)

# ── FINDINGS (paste actual numbers from your analysis runs) ───────────────────

DASHBOARD_URL = "https://YOUR-APP.streamlit.app"   # update after deployment

FINDINGS = [
    {
        "q":      "Q1 - The Toss Trap",
        "text":   (
            "IPL toss winners convert to match winners only 51.8% of the time across "
            "1,169 valid matches - statistically indistinguishable from a coin flip. "
            "Teams have shifted overwhelmingly toward choosing to field (50% in 2008-12 to "
            "76% in 2018-25), yet the fielding-first win rate is declining (55.7% to 53.7%). "
            "Venue segmentation reveals the real story: Jaipur shows >70% toss win rate "
            "in Era 3 while Dubai shows <42%. Teams are optimising hard for the wrong KPI."
        ),
    },
    {
        "q":      "Q2 - Death Over Specialists",
        "text":   (
            "Among 89 bowlers with at least 200 death-over balls (overs 16-20), "
            "Malinga and Bollinger lead on combined economy and wicket rate. "
            "Economy rate is adjusted for opposition strength - a bowler conceding "
            "9 RPO against Mumbai Indians deserves more credit than one doing the same "
            "against a weaker side. The scatter reveals the rarest profile in T20 cricket: "
            "bowlers who both contain and take wickets when pressure is highest."
        ),
    },
    {
        "q":      "Q3 - The Run Rate Revolution",
        "text":   (
            "All three phases of IPL innings have become more batting-friendly since 2008. "
            "Powerplay scoring rose +2.00 RPO (2008 to 2025) as openers became increasingly "
            "aggressive. Death-over scoring spiked sharply in 2022 (+1.04 RPO in one season), "
            "coinciding with the rise of specialist finishers. Middle overs show the "
            "smallest shift - that phase remains the most contested battleground in T20. "
            "This decomposition shows not just that the game changed, but when and where."
        ),
    },
    {
        "q":      "Q4 - Team Strategy Alpha",
        "text":   (
            "Expected runs are calculated as the average innings score at the same venue, "
            "in the same innings position, in the same era. Gujarat Titans and Chennai Super "
            "Kings lead at +3.7 runs per innings above venue expectation. Delhi Capitals "
            "are the lowest at -4.0 runs per innings. This metric controls for venue context "
            "so that a team scoring 180 at Chepauk is evaluated differently from one scoring "
            "180 at Wankhede - revealing coaching and strategic quality beyond raw talent."
        ),
    },
    {
        "q":      "Q5 - Home Ground Advantage",
        "text":   (
            "Home advantage is real but franchise-specific. Rajasthan Royals show the "
            "strongest edge (68.1% at home vs 42.0% away, +26.1pp differential), "
            "likely driven by their spin-friendly Jaipur wicket. Gujarat Titans and "
            "Lucknow Super Giants - newer franchises - actually perform better away than "
            "at home (-11pp and -13pp), suggesting they rely on squad quality over venue "
            "familiarity. The 2020 UAE season (all-neutral) is excluded and serves as a "
            "natural experiment confirming the home advantage effect."
        ),
    },
]


# ── PDF GENERATION ────────────────────────────────────────────────────────────

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(26, 26, 46)
        self.cell(0, 12, "IPL Cricket Analytics Dashboard", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, "Five Data Questions | IPL 2008-2025 | Angajala Gautam Raju",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 5, f"Live Dashboard: {DASHBOARD_URL}", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5,
                  "Data: Kaggle (chaitu20/ipl-dataset2008-2025) · Stack: Python, Pandas, Plotly, Streamlit",
                  align="C")


pdf = PDF()
pdf.set_margins(left=18, top=16, right=18)
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=20)

# Lead finding box
pdf.set_fill_color(255, 255, 220)
pdf.set_draw_color(180, 180, 100)
pdf.set_line_width(0.4)
pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(26, 26, 46)
pdf.cell(0, 7, "Lead Finding - The Toss Trap", new_x="LMARGIN", new_y="NEXT", fill=True)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(50, 50, 50)
pdf.multi_cell(0, 6,
    "Teams optimise intensely for a toss that explains almost no outcome variance (51.8% win rate). "
    "The IPL's version of over-indexing on the wrong KPI - but venue segmentation reveals where it "
    "actually matters.",
    fill=True)
pdf.ln(5)

# 5 findings
for finding in FINDINGS:
    # Section header
    pdf.set_fill_color(240, 240, 250)
    pdf.set_draw_color(150, 150, 200)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 26, 100)
    pdf.cell(0, 7, finding["q"], new_x="LMARGIN", new_y="NEXT", fill=True, border="L")
    # Body
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5.5, finding["text"])
    pdf.ln(3)

out_path = "outputs/ipl_insights.pdf"
pdf.output(out_path)
print(f"Saved: {out_path}")
print(f"\nRemember to update DASHBOARD_URL in this script after deployment.")
