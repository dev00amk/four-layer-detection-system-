# Tableau dashboard specification

Use `data/gold/tableau_export.csv`.

1. KPI tiles: trips scored, CRITICAL+ count, mean score, graph-flag rate.
2. Risk-band distribution: horizontal bars sorted by severity.
3. Four-layer scatter: XGBoost probability vs Isolation Forest score, color by band, shape by graph flag.
4. Investigation queue: driver, trip, score, band, SQL hits, graph flag.

Apply a global risk-band filter and use the investigation queue as the dashboard action target.

