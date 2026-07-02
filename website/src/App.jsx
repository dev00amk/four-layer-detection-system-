import { useEffect, useMemo, useState } from "react";
import caseGraph from "../../dashboards/case_001_graph.png";

const repoUrl = "https://github.com/dev00amk/four-layer-detection-system-";

const layers = [
  {
    id: "01",
    label: "SQL signals",
    score: "12 / 25",
    threshold: "> 5",
    copy: "Transparent rules surface impossible travel, shared devices, payout changes, incentive abuse, and other investigator-readable behaviors.",
  },
  {
    id: "02",
    label: "Isolation Forest",
    score: "0.681",
    threshold: "> 0.60",
    copy: "Unsupervised scoring catches unusual behavior without pretending that every anomaly is fraud.",
  },
  {
    id: "03",
    label: "XGBoost + SHAP",
    score: "1.000",
    threshold: "> 0.50",
    copy: "Supervised probability is paired with reason codes so investigators can challenge the model, not merely receive its verdict.",
  },
  {
    id: "04",
    label: "Entity graph",
    score: "1.2×",
    threshold: "ring = 1",
    copy: "Shared devices, banks, campaigns, and stores connect accounts that look ordinary when reviewed one at a time.",
  },
];

const capabilities = [
  ["25", "auditable SQL signals"],
  ["04", "independent detection layers"],
  ["06", "fraud families mapped"],
  ["12K", "synthetic demo rows"],
];

const skillGroups = [
  {
    id: "01",
    label: "Detection",
    heading: "Fraud detection & behavioral analysis",
    summary: "Turns mixed platform telemetry into reviewable risk hypotheses without collapsing anomaly into guilt.",
    items: [
      {
        skill: "Behavioral segmentation, trend analysis, and anomaly detection",
        proof: "7-, 30-, and 90-day behavioral windows, trend deltas, Isolation Forest, and exploratory correlation analysis.",
        href: `${repoUrl}/blob/main/sentinel/features.py`,
      },
      {
        skill: "Mixed-signal risk interpretation",
        proof: "GPS, device, payout, metadata, model, and graph evidence converge in one bounded composite score.",
        href: `${repoUrl}/blob/main/docs/DEPARTMENT_CORE_MANDATE.md`,
      },
      {
        skill: "Context-aware false-positive control",
        proof: "Legitimate GPS drift, carrier NAT, power-user behavior, and shared-household scenarios are documented as exclusions.",
        href: `${repoUrl}/blob/main/docs/FAILURE_MODE_ANALYSIS.md`,
      },
    ],
  },
  {
    id: "02",
    label: "Signals",
    heading: "Fraud signal development & model support",
    summary: "Translates attacker opportunity into measurable behavior, testable thresholds, and governed model feedback.",
    items: [
      {
        skill: "SQL signal and composite-rule development",
        proof: "25 version-controlled DuckDB signals with fraud type, threshold rationale, FP risk, and mitigation.",
        href: `${repoUrl}/tree/main/sql/signals`,
      },
      {
        skill: "Hypothesis testing and threshold refinement",
        proof: "Detection strategies define evidence standards, modeled tradeoffs, operational cost, and monitoring plans.",
        href: `${repoUrl}/blob/main/docs/DETECTION_STRATEGY.md`,
      },
      {
        skill: "Model QA and structured feedback loops",
        proof: "SHAP explanations, drift and fairness gates, confirmed outcomes, appeals, and retraining feedback are operationalized.",
        href: `${repoUrl}/blob/main/docs/SIGNAL_PRIORITIZATION.md`,
      },
    ],
  },
  {
    id: "03",
    label: "Investigations",
    heading: "Investigation & evidence documentation",
    summary: "Builds a reproducible chain from alert intake to defensible decision, with explicit human review.",
    items: [
      {
        skill: "Structured investigation and case management",
        proof: "An eight-step SOP and integrity-hashed case files cover intake, exclusions, escalation, decision, and closure.",
        href: `${repoUrl}/blob/main/docs/INVESTIGATOR_PLAYBOOK.md`,
      },
      {
        skill: "OSINT, identity, device, and geolocation enrichment",
        proof: "Five structured enrichment families produce step-level audit records; simulation is clearly separated from live vendors.",
        href: `${repoUrl}/blob/main/sentinel/osint.py`,
      },
      {
        skill: "Adversarial thinking and emerging-vector analysis",
        proof: "A fraud-technique library maps seven attack techniques to a ten-stage abuse lifecycle and mitigation coverage.",
        href: `${repoUrl}/blob/main/docs/FRAUD_TECHNIQUES.md`,
      },
    ],
  },
  {
    id: "04",
    label: "Reporting",
    heading: "Cross-functional collaboration & reporting",
    summary: "Converts operational evidence into decisions Product, Legal, Compliance, Engineering, and Care can act on.",
    items: [
      {
        skill: "Audience-specific operational briefings",
        proof: "Separate Product, Legal, Engineering, and Care Operations briefs translate the same case into relevant actions.",
        href: `${repoUrl}/blob/main/docs/CROSS_FUNCTIONAL_BRIEFING.md`,
      },
      {
        skill: "Product-control and policy requirements",
        proof: "Detection gaps become step-up verification, payout holds, instrumentation requests, ownership, and monitoring plans.",
        href: `${repoUrl}/blob/main/docs/OPERATIONAL_RISK.md`,
      },
      {
        skill: "Audit readiness, QA trends, and SOP governance",
        proof: "Evidence standards, appeals, model validation, analyst QA, decision logs, and review cadence are documented.",
        href: `${repoUrl}/blob/main/docs/GOVERNANCE.md`,
      },
    ],
  },
];

function useReveal() {
  useEffect(() => {
    const nodes = document.querySelectorAll("[data-reveal]");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);
}

export function App() {
  const [theme, setTheme] = useState("dark");
  const [activeLayer, setActiveLayer] = useState(0);
  const [activeSkill, setActiveSkill] = useState(0);
  const [graphOpen, setGraphOpen] = useState(false);
  const active = useMemo(() => layers[activeLayer], [activeLayer]);
  const selectedSkill = useMemo(() => skillGroups[activeSkill], [activeSkill]);

  useReveal();

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") setGraphOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <header className="terminal-bar" aria-label="Site header">
        <div className="window-dots" aria-hidden="true"><i /><i /><i /></div>
        <a className="terminal-path" href="#top">~/sentinel — CASE_001.md</a>
        <button
          className="theme-toggle"
          type="button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? "light mode" : "dark mode"}
        </button>
      </header>

      <main id="top">
        <section className="hero shell">
          <div className="eyebrow"><span className="live-dot" /> portfolio case study / fraud operations</div>
          <h1>sentinel<span aria-hidden="true">▋</span></h1>
          <p className="hero-line">Four signals disagree. One reviewable case tells the truth.</p>
          <p className="hero-copy">
            // A four-layer fraud decision system that turns behavioral signals,
            anomaly detection, explainable ML, and entity graphs into evidence an
            investigator can actually use.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="#case">[ inspect CASE_001 ]</a>
            <a className="button" href={repoUrl} target="_blank" rel="noreferrer">[ view source ]</a>
          </div>
          <a className="proof-strip" href="#architecture">
            <span><b>12 / 25</b> SQL signals fired</span>
            <span><b>10 / 10</b> composite risk</span>
            <span><b>CRITICAL+</b> review queue</span>
            <span aria-hidden="true">scroll</span>
          </a>
        </section>

        <section className="section shell" id="architecture" data-reveal>
          <p className="section-label">## the_operating_problem</p>
          <h2>A fraud detector is easy.<br />A defensible decision is harder.</h2>
          <div className="split-copy">
            <p>
              Operations teams need more than a risk score. They need traceable
              evidence, false-positive controls, explainable escalation, and a
              record that survives review.
            </p>
            <p className="comment">
              // Sentinel is designed as an investigator-enablement workflow:
              detect → corroborate → enrich → prioritize → document.
            </p>
          </div>
          <div className="capability-grid" aria-label="Project capabilities">
            {capabilities.map(([value, label]) => (
              <div className="capability" key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="section shell case-section" id="case" data-reveal>
          <div className="section-heading-row">
            <div>
              <p className="section-label">## worked_case / CASE_001</p>
              <h2>Follow the evidence,<br />layer by layer.</h2>
            </div>
            <div className="case-badge">
              <span>composite</span>
              <strong>10 / 10</strong>
              <em>CRITICAL+</em>
            </div>
          </div>

          <div className="case-console">
            <div className="layer-tabs" role="tablist" aria-label="Detection layers">
              {layers.map((layer, index) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeLayer === index}
                  className={activeLayer === index ? "active" : ""}
                  onClick={() => setActiveLayer(index)}
                  key={layer.id}
                >
                  <span>{layer.id}</span> {layer.label}
                </button>
              ))}
            </div>
            <div className="layer-detail" role="tabpanel" aria-live="polite">
              <div className="score-line">
                <span>observed</span><strong>{active.score}</strong>
                <span>threshold</span><strong>{active.threshold}</strong>
                <mark>✓ fired</mark>
              </div>
              <h3>{active.label}</h3>
              <p>{active.copy}</p>
              <div className="progress-track" aria-hidden="true">
                <i style={{ width: `${58 + activeLayer * 11}%` }} />
              </div>
            </div>
          </div>
        </section>

        <section className="section shell graph-section" data-reveal>
          <div className="graph-copy">
            <p className="section-label">## the_connection</p>
            <h2>Two drivers.<br />One hidden ring.</h2>
            <p>
              CASE_001 connects two driver accounts through a shared device, bank,
              campaign, and store. The graph multiplier strengthens corroborated
              evidence; it does not replace human review.
            </p>
            <button className="text-link" type="button" onClick={() => setGraphOpen(true)}>
              [ expand evidence graph ]
            </button>
          </div>
          <button className="graph-frame" type="button" onClick={() => setGraphOpen(true)} aria-label="Expand CASE_001 entity graph">
            <span>case_001_graph.png</span>
            <img src={caseGraph} alt="Entity graph connecting two driver accounts to a shared device, bank, campaign, and store" />
          </button>
        </section>

        <section className="section shell" data-reveal>
          <p className="section-label">## control_before_action</p>
          <h2>The model recommends.<br />The evidence decides.</h2>
          <div className="control-grid">
            <article>
              <span>01</span>
              <h3>Corroborate</h3>
              <p>No single signal becomes an enforcement decision. Independent layers must agree.</p>
            </article>
            <article>
              <span>02</span>
              <h3>Explain</h3>
              <p>SQL flags, SHAP reasons, graph relationships, and provenance stay attached to the case.</p>
            </article>
            <article>
              <span>03</span>
              <h3>Escalate</h3>
              <p>Queue thresholds, analyst playbooks, appeal paths, and audit logs constrain action.</p>
            </article>
          </div>
        </section>

        <section className="section shell skills-section" id="skills" data-reveal>
          <div className="section-heading-row skills-heading">
            <div>
              <p className="section-label">## role_capability_map</p>
              <h2>Fraud operations.<br />Evidence in the project.</h2>
            </div>
            <p className="comment">
              // Each capability links to code, analysis, or a documented operating control.
            </p>
          </div>

          <div className="skills-console">
            <div className="skill-nav" role="tablist" aria-label="Role capability groups">
              {skillGroups.map((group, index) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeSkill === index}
                  className={activeSkill === index ? "active" : ""}
                  onClick={() => setActiveSkill(index)}
                  key={group.id}
                >
                  <span>{group.id}</span>
                  <strong>{group.label}</strong>
                </button>
              ))}
            </div>

            <div className="skill-panel" role="tabpanel" aria-live="polite">
              <p className="skill-kicker">essential function / {selectedSkill.id}</p>
              <h3>{selectedSkill.heading}</h3>
              <p className="skill-summary">{selectedSkill.summary}</p>
              <div className="skill-evidence">
                {selectedSkill.items.map((item) => (
                  <a href={item.href} target="_blank" rel="noreferrer" key={item.skill}>
                    <span>demonstrated</span>
                    <strong>{item.skill}</strong>
                    <p>{item.proof}</p>
                    <em>inspect evidence</em>
                  </a>
                ))}
              </div>
            </div>
          </div>

          <div className="tool-belt" aria-label="Demonstrated tools and domains">
            <span>SQL / DuckDB</span>
            <span>Python / pandas</span>
            <span>Isolation Forest</span>
            <span>XGBoost / SHAP</span>
            <span>OSINT</span>
            <span>Entity graphs</span>
            <span>Case management</span>
            <span>Dashboard specifications</span>
          </div>
        </section>

        <section className="section shell run-section" data-reveal>
          <p className="section-label">## run_the_demo</p>
          <h2>One command.<br />A complete evidence trail.</h2>
          <div className="command-box">
            <span>$</span>
            <code>python -m sentinel.demo</code>
            <button
              type="button"
              onClick={() => navigator.clipboard?.writeText("python -m sentinel.demo")}
              aria-label="Copy demo command"
            >
              copy
            </button>
          </div>
          <p className="comment">
            // Runs locally on synthetic data. No 170 MB Kaggle download required.
          </p>
          <div className="final-actions">
            <a className="button primary" href={`${repoUrl}#quick-start`} target="_blank" rel="noreferrer">[ run sentinel ]</a>
            <a className="button" href={`${repoUrl}/blob/main/docs/DEMO_WALKTHROUGH.md`} target="_blank" rel="noreferrer">[ read walkthrough ]</a>
          </div>
        </section>
      </main>

      <footer className="terminal-bar footer">
        <p>// portfolio implementation — not a Walmart system.</p>
        <a href={repoUrl} target="_blank" rel="noreferrer">GitHub</a>
      </footer>

      {graphOpen && (
        <div className="modal" role="dialog" aria-modal="true" aria-label="Expanded CASE_001 entity graph" onClick={() => setGraphOpen(false)}>
          <button type="button" onClick={() => setGraphOpen(false)}>close ×</button>
          <img src={caseGraph} alt="Expanded CASE_001 entity graph" onClick={(event) => event.stopPropagation()} />
        </div>
      )}
    </>
  );
}
