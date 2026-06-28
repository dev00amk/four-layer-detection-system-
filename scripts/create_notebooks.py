"""Build reproducible reader-facing notebooks with nbformat."""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
NOTEBOOKS.mkdir(exist_ok=True)


def write(name, title, purpose, cells):
    nb = nbf.v4.new_notebook()
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["cells"] = [
        nbf.v4.new_markdown_cell(f"# {title}\n\n## tl;dr\n\nRun the pipeline first; this notebook derives its findings from the generated silver and gold artifacts."),
        nbf.v4.new_markdown_cell(f"## Context & Methods\n\n{purpose}\n\n### Key Assumptions\n\nSynthetic telemetry is deterministic and illustrative; IEEE-CIS labels remain the supervised target."),
        *cells,
        nbf.v4.new_markdown_cell("## Takeaways\n\nUse the executed charts and tables to explain how complementary detection layers reduce blind spots while preserving analyst review."),
    ]
    nbf.write(nb, NOTEBOOKS / name)


setup = nbf.v4.new_code_cell(
    "from pathlib import Path\nimport sys\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n"
    "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
    "sys.path.insert(0, str(ROOT))\n"
    "df = pd.read_parquet(ROOT/'data/silver/spark_driver_trips.parquet')\n"
    "print(df.shape, f'fraud rate={df.isFraud.mean():.3%}')"
)
write(
    "01_eda.ipynb",
    "Project Sentinel — Exploratory Data Analysis",
    "Validate class imbalance and the separability of enriched last-mile delivery risk signals.",
    [
        nbf.v4.new_markdown_cell("## Data"),
        setup,
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell(
            "fig, axes = plt.subplots(2, 2, figsize=(12, 9))\n"
            "df.isFraud.value_counts().sort_index().plot.bar(ax=axes[0,0], title='Class imbalance')\n"
            "sns.violinplot(data=df.sample(min(5000,len(df)), random_state=42), x='isFraud', y='TransactionAmt', ax=axes[0,1]); axes[0,1].set_ylim(0,500)\n"
            "df.groupby('DeviceType', dropna=False).isFraud.mean().sort_values().plot.bar(ax=axes[1,0], title='Fraud rate by device type')\n"
            "sns.scatterplot(data=df.sample(min(3000,len(df)), random_state=42), x='pickup_lon', y='pickup_lat', hue='isFraud', alpha=.5, ax=axes[1,1]); axes[1,1].set_title('Pickup GPS anomaly surface')\n"
            "plt.tight_layout()"
        ),
        nbf.v4.new_code_cell(
            "features=['isFraud','TransactionAmt','dist1','C1','C2','geofence_dist_m','emulator_flag','gps_mock_flag','refund_count_30d','trip_distance_km']\n"
            "plt.figure(figsize=(9,7)); sns.heatmap(df[features].corr(numeric_only=True), cmap='vlag', center=0); plt.title('Risk-feature correlation')"
        ),
    ],
)
write(
    "04_ml_model.ipynb",
    "Project Sentinel — Four-Layer Model",
    "Review validated model metrics, feature importance, and the benchmark comparison.",
    [
        nbf.v4.new_markdown_cell("## Data"),
        setup,
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell(
            "import json\nmetrics=json.loads((ROOT/'data/models/metrics.json').read_text())\n"
            "benchmark={'auc_roc':.918,'auc_pr':.891}\n"
            "pd.DataFrame({'demo_or_local':metrics,'reference_benchmark':benchmark})"
        ),
        nbf.v4.new_code_cell(
            "from sentinel.model import SentinelModel\n"
            "from xgboost import XGBClassifier\n"
            "X=df[SentinelModel.XGB_FEATURES].fillna(-999); y=df.isFraud.astype(int)\n"
            "m=XGBClassifier(n_estimators=80,max_depth=4,eval_metric='logloss',random_state=42).fit(X,y)\n"
            "pd.Series(m.feature_importances_,index=X.columns).nlargest(10).sort_values().plot.barh(title='Top 10 model features')"
        ),
    ],
)
write(
    "05_graph_analysis.ipynb",
    "Project Sentinel — Fraud Ring Analysis",
    "Show how shared device, payout, and network entities expose coordination that row-level classifiers miss.",
    [
        nbf.v4.new_markdown_cell("## Data"),
        nbf.v4.new_code_cell(
            "from pathlib import Path\nimport sys\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport networkx as nx\n"
            "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
            "sys.path.insert(0, str(ROOT))\n"
            "rings=pd.read_csv(ROOT/'data/gold/graph/fraud_rings.csv')\n"
            "rings.groupby('ring_id').ring_size.max().nlargest(10).to_frame()"
        ),
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell("rings.groupby('ring_id').ring_size.max().plot.hist(bins=20, title='Fraud ring size distribution'); plt.xlabel('Drivers per component')"),
        nbf.v4.new_code_cell(
            "trips=pd.read_parquet(ROOT/'data/silver/spark_driver_trips.parquet')\n"
            "case_rows=trips[trips.device_id.eq('DEV_CASE001')]\n"
            "drivers=sorted(case_rows.driver_id.unique())[:2]\n"
            "case_graph=nx.Graph()\n"
            "for driver in drivers:\n"
            "    case_graph.add_node(driver, kind='driver')\n"
            "    for entity,kind in [('DEV_CASE001','device'),('BANK_CASE001','bank'),('CMP_CASE001','campaign')]:\n"
            "        case_graph.add_node(entity, kind=kind); case_graph.add_edge(driver, entity)\n"
            "colors={'driver':'coral','device':'mediumpurple','bank':'goldenrod','campaign':'gray'}\n"
            "pos={'DEV_CASE001':(0,1),'BANK_CASE001':(0,0),'CMP_CASE001':(0,-1),drivers[0]:(-1,0),drivers[1]:(1,0)}\n"
            "plt.figure(figsize=(10,6)); nx.draw(case_graph,pos,with_labels=True,node_size=2600,font_size=9,font_weight='bold',node_color=[colors[case_graph.nodes[n]['kind']] for n in case_graph],edge_color='#777',width=2)\n"
            "plt.title('CASE_001 — Two drivers linked by one device, bank, and campaign')\n"
            "plt.tight_layout(); plt.savefig(ROOT/'dashboards/case_001_graph.png',dpi=180,bbox_inches='tight'); plt.show()"
        ),
        nbf.v4.new_markdown_cell(
            "### CASE_001 interpretation\n\n"
            "Two driver accounts converge on the same device, payout account, and incentive campaign. "
            "Each row can look individually plausible, but the entity graph exposes coordinated control "
            "and cash-out infrastructure—precisely the pattern a row-based classifier can miss."
        ),
    ],
)
print("Created 3 notebooks")
