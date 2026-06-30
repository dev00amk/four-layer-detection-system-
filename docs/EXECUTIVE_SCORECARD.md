# Trust Intelligence Executive Scorecard
## Project Sentinel — Weekly Program Health Report

**Owner:** Trust Intelligence Program Lead
**Audience:** CEO, CFO, VP Operations, General Counsel, VP Product
**Cadence:** Weekly (distributed every Monday by 09:00 local); settlement-cycle summary distributed within 2 business days of each settlement close
**Last updated:** 2026-06-29

---

## How to Read This Scorecard

Each metric shows: **current value | target | status (green / amber / red)**

- Green: within target
- Amber: within 20% of threshold — monitor closely
- Red: threshold breached — action required, see recommended actions section

Status is automatically calculated from `data/models/metrics.json`, `data/labels/dispositions.jsonl`, and `data/drift/alerts.jsonl` each settlement cycle. The program lead prepares the narrative and recommended actions section.

---

## Section 1: Financial Outcomes

*Answers: Is the program preventing meaningful fraud loss? Is it paying for itself?*

| Metric | Current | Target | Status | Owner |
|--------|---------|--------|--------|-------|
| Estimated fraud loss prevented (settlement cycle) | [from BUSINESS_IMPACT model] | > $X | - | Trust Program Lead |
| Fraud loss prevented (YTD) | [cumulative] | > $Y | - | Trust Program Lead |
| Confirmed fraud cases actioned (cycle) | [from dispositions.jsonl] | Track | - | Trust Program Lead |
| Program operating cost (cycle) | [investigator hours x rate + infra] | < 20% of loss prevented | - | Finance |
| Net ROI (loss prevented / program cost) | [calculated] | > 5:1 | - | Finance |

**Threshold alerts:**
- Red if confirmed fraud loss prevented < 50% of target for 2 consecutive cycles
- Red if program cost exceeds 30% of loss prevented in any cycle

---

## Section 2: Detection Quality

*Answers: Is the detection system working? Is it getting better or worse?*

| Metric | Current | Target | Status | Owner |
|--------|---------|--------|--------|-------|
| XGBoost AUC-ROC (latest run) | [from metrics.json] | > 0.85 | - | Engineering |
| XGBoost AUC-PR (latest run) | [from metrics.json] | > 0.75 | - | Engineering |
| CRITICAL cases generated (cycle) | [from metrics.json] | Track (capacity: 25/run) | - | Trust Program Lead |
| PSI drift score (latest run) | [from drift/alerts.jsonl] | < 0.10 | - | Engineering |
| Novel pattern alerts (Isolation Forest high-score, no rule match) | [count] | Track | - | Trust Program Lead |

**Threshold alerts:**
- Red if AUC-ROC drops > 5pp from baseline in any run
- Red if PSI > 0.25 (significant drift)
- Amber if PSI 0.10-0.25 (moderate drift — monitor)

---

## Section 3: Investigator Operations

*Answers: Are investigators keeping up? Are cases being resolved accurately and on time?*

| Metric | Current | Target | Status | Owner |
|--------|---------|--------|--------|-------|
| Cases in queue (open) | [live count] | < 25 | - | Investigations Lead |
| Cases resolved within SLA (5 business days) | [from dispositions.jsonl] | > 90% | - | Investigations Lead |
| False-positive rate (confirmed dispositions) | [from feedback.py fp_rate()] | < 15% | - | Trust Program Lead |
| Appeal overturn rate | [from feedback.py appeal_overturn_rate()] | < 10% | - | Trust Program Lead |
| Cases awaiting Legal sign-off > 10 business days | [count] | 0 | - | Legal |

**Threshold alerts:**
- Red if FP rate > 15% (retraining trigger + threshold review required)
- Red if appeal overturn rate > 10% (investigation SOP review required)
- Red if queue > 25 open cases (capacity breach — escalate for resourcing)

---

## Section 4: Fairness and Compliance

*Answers: Are we treating contractors equitably? Are we legally defensible?*

| Metric | Current | Target | Status | Owner |
|--------|---------|--------|--------|-------|
| Four-fifths rule: device tier (older_android / newer_android / ios) | [from fairness.py] | All groups pass | - | Trust Program Lead |
| Four-fifths rule: geography | [from fairness.py] | All groups pass | - | Trust Program Lead |
| Statistical parity delta (max across groups) | [from fairness.py] | < 5pp | - | Trust Program Lead |
| Open regulatory inquiries | [count] | 0 | - | Legal |
| Adverse actions with complete evidence pack (SHA-256 verified) | [audit sample] | 100% | - | Compliance |

**Threshold alerts:**
- Red if any group fails the four-fifths rule (pipeline blocked by fairness.py — requires Legal review before next run)
- Red if any open regulatory inquiry goes unacknowledged for > 5 business days

---

## Section 5: Model and Governance Health

*Answers: Is the system being maintained? Are governance commitments being met?*

| Metric | Current | Target | Status | Owner |
|--------|---------|--------|--------|-------|
| Disposition labels collected (total) | [from feedback.py] | > 500 (retraining trigger) | - | Trust Program Lead |
| Days since last model retraining | [date] | < 90 days | - | Engineering |
| Signal library: signals in 'sunset' status | [count] | 0 (retire promptly) | - | Trust Program Lead |
| Governance document reviews overdue | [count] | 0 | - | Trust Program Lead |
| Incentive programs awaiting Trust review | [count] | 0 | - | Trust Program Lead |

---

## Section 6: Narrative and Recommended Actions

*Completed by Trust Program Lead each cycle. Max 200 words.*

**This cycle's headline:**
> [One sentence: the most important thing leadership needs to know this week]

**What changed:**
> [2-3 sentences: notable detections, signal changes, product events that affected fraud patterns]

**Recommended actions:**
> [Bulleted list of decisions or resources needed from leadership this cycle. Each item: action, owner, deadline]

**Flags for the next cycle:**
> [What to watch — leading indicators of potential problems not yet at threshold]

---

## Appendix: Metric Calculation Reference

| Metric | Source | Calculation |
|--------|--------|------------|
| Fraud loss prevented | BUSINESS_IMPACT.md loss model x confirmed fraud cases | (avg loss per attack family) x (confirmed fraud cases by family) |
| FP rate | data/labels/dispositions.jsonl | false_positive / (false_positive + confirmed_fraud) |
| Appeal overturn rate | data/labels/dispositions.jsonl | appeal_upheld / (appeal_upheld + appeal_denied) |
| PSI | data/drift/alerts.jsonl | Population Stability Index vs baseline; see sentinel/drift.py |
| Four-fifths ratio | data/fairness/alerts.jsonl | adverse_rate(group) / adverse_rate(best_group); see sentinel/fairness.py |
| Net ROI | Finance | (fraud loss prevented - program cost) / program cost |

---

*This scorecard template is version-controlled. Changes to metric definitions or thresholds require sign-off from Trust Program Lead, Finance, and Legal before the change takes effect.*
