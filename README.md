# Bertus Delivery Performance Dashboard

![Python](https://img.shields.io/badge/Python-3.x-blue)
![pandas](https://img.shields.io/badge/pandas-data%20cleaning-150458)
![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B)
![Plotly](https://img.shields.io/badge/Plotly-visualization-3F4F75)
![Power BI](https://img.shields.io/badge/Power%20BI-dashboard-F2C811)

An end to end delivery performance analytics project, built twice: once in Python (pandas, Plotly, Streamlit) and once in Power BI (Power Query, DAX), on the same dataset. Built to practice the exact SLA and delay reporting an operations or supply chain analyst role would own.

## The business problem

Bertus Distributie is a physical media wholesale distributor (vinyl, CD, DVD, merchandise) shipping to independent stores, retail chains, and online retailers across the Netherlands and neighboring countries. A distributor like this runs on carrier SLAs it doesn't fully control, so the recurring operational question is: **which carriers and routes are actually costing us on-time performance, why, and what should change about how we route shipments?** That's the question a logistics or supply chain analyst is hired to answer with data instead of guesswork — and the one this project is built to practice end to end, from dirty raw data to a recommendation someone could act on.

This project simulates that scenario with 140 shipment records, deliberately shipped "dirty": plain text dates, no precomputed on-time flags or delay figures, so real cleaning work has to happen before any analysis can start, and the output has to stand on its own as something you'd actually hand to an operations manager.

## The data

The raw dataset (`data/bertus_shipments_raw.csv`) is 140 synthetic shipment records built to mirror Bertus's real business: physical media (vinyl, CD, DVD, and merchandise) shipped to three customer types (independent stores, retail chains, online retailers) across six destination countries (Netherlands, Germany, Belgium, France, United Kingdom, United States) through five carriers (PostNL, DHL, DPD, GLS, UPS). Each row carries an order date, a promised delivery date, an actual delivery date, an order value in EUR, and, only when the shipment ran late, a delay reason (Carrier delay, Customs hold, Stock shortage, Documentation error, or Weather).

It ships dirty in two ways that mirror how operational data usually looks before an analyst gets to it. First, the three date fields are plain text, not real date objects, so nothing can be compared or aggregated until they're parsed. Second, none of the fields an analyst actually needs exist yet: whether a shipment was late, by how many days, and which calendar month it belongs to all have to be derived rather than read off the sheet. The delay_reason field is blank for the 103 shipments that arrived on time, which also has to be handled explicitly rather than silently dropped or mistaken for missing data.

## How the numbers are calculated

Everything downstream comes from three derived fields, computed the same way in both the Python and Power BI versions:

- **delay_days** — actual delivery date minus promised delivery date, in days. Positive means the shipment arrived after its promise date; zero or negative means on time or early.
- **is_late** — true when delay_days is greater than zero. Every other metric in the dashboard rolls up from this one flag.
- **order_month** — the order date truncated to its calendar month, used to build the on-time trend line.

From there, the headline metrics are straightforward aggregates over is_late and order_value_eur. On-time rate is one minus the average of is_late, expressed as a percentage, i.e. the share of shipments that did not run late. Average delay when late is the mean of delay_days, but only over the rows where is_late is true, since on-time shipments have no delay to average in. On-time rate by carrier, by month, and by destination country is the same on-time-rate formula, just grouped by that column instead of computed over the whole dataset. The delay reason breakdown is a count of delay_reason, filtered to late shipments only.

In the Python version this is plain pandas: parse the three date columns with `pd.to_datetime`, subtract to get delay_days, threshold to get is_late, fill the blank delay_reason values with "On time", then `.groupby()` for every breakdown. The Power BI version splits the same logic across two layers: Power Query (M) does the date parsing and column derivation at load time, and DAX measures do the ratio and average calculations, so the on-time rate and average delay recalculate live as the report's carrier, country, or customer-type filters change.

## Key findings & recommendations

Overall on-time rate is 73.6%. Of the 140 shipments, 37 ran late, accounting for EUR 31,094 of the EUR 126,797 in total order value — close to a quarter of everything shipped. That's frequent enough, and touches enough order value, to justify a standing SLA review rather than a one-off fix.

GLS is disproportionately responsible for the lateness. It carries 17.9% of total shipment volume (25 of 140 shipments) but accounts for 27% of all late shipments (10 of 37), with EUR 8,937 of delayed order value sitting on GLS shipments alone. PostNL, by contrast, is the most reliable carrier at a 78.8% on-time rate. **Recommendation:** reroute GLS's weather-exposed and cross-border lanes to PostNL or DHL first, rather than spreading a fix evenly across all five carriers — the data points to one carrier as the highest-leverage place to start, not a general policy change.

Weather is the single largest cause of delay, responsible for 27% of all late shipments and EUR 5,984 of exposed order value, ahead of stock shortages (21.6%) and customs holds (18.9%). **Recommendation:** build a weather-contingent buffer into promised delivery windows on the routes most exposed to it, instead of committing to one flat SLA regardless of season or carrier — the alternative is repeatedly promising dates the business can't reliably hit on some lanes.

On-time performance dropped sharply from June to July 2026. **Recommendation:** before treating that drop as a new baseline, check whether it tracks a change in carrier mix, order volume, or seasonal weather exposure over the same window — a trend like this is a starting point for investigation, not a finding to act on by itself.

## Screenshots

**Streamlit version**

![Streamlit dashboard screenshot](screenshots/streamlit_dashboard.png)

**Power BI version**

![Power BI dashboard screenshot](screenshots/powerbi_dashboard.png)

## Two tools, same data, deliberately

Built twice on purpose, to compare how the same analysis looks in a coding tool versus a business intelligence tool:

| | Python / Streamlit | Power BI |
|---|---|---|
| Data cleaning | pandas | Power Query (M language) |
| Calculations | plain Python | DAX measures |
| Visualization | Plotly | native Power BI visuals |
| How to open it | `streamlit run app.py` | open `bertus_delivery_dashboard.pbix` |

## Project structure

```
bertus_delivery_dashboard/
├── app.py                              # Streamlit dashboard (Python)
├── bertus_delivery_dashboard.pbix      # Power BI dashboard
├── requirements.txt
├── data/
│   └── bertus_shipments_raw.csv        # raw, deliberately uncleaned shipment data
├── scripts/
│   └── generate_raw_data.py            # generates the synthetic dataset
├── notebooks/
│   ├── Bertus_Delivery_Analysis.ipynb
│   ├── Bertus_Delivery_Walkthrough.ipynb
│   └── build_notebook.py
├── reference/
│   └── Bertus Delivery Performance Dashboard (finished reference example).xlsx
└── screenshots/
    ├── streamlit_dashboard.png
    └── powerbi_dashboard.png
```

## How to run it

**Streamlit version:**
```
pip install -r requirements.txt
streamlit run app.py
```
Then open the local URL it gives you (usually `http://localhost:8501`).

**Power BI version:**
Open `bertus_delivery_dashboard.pbix` directly in Power BI Desktop (free from Microsoft).

## Data note

All data is synthetic, generated by `scripts/generate_raw_data.py`. It is modeled on Bertus Distributie's real business context (product types, carriers, destination countries) but contains no real company data.

## About

Built by Adrian Vanderlinder, moving into logistics, operations and data roles.

[LinkedIn](https://www.linkedin.com/in/adrian-vanderlinder-azcona-59b1299b) · [GitHub](https://github.com/adrianjva18) · adrian.azcona18@gmail.com
