# DECISION_LOG.md — Project Sentinel

> **Purpose:** This log records significant operational and architectural decisions
> made during the development and operation of Project Sentinel. Each entry documents
> the problem, options considered, decision made, rationale, expected impact,
> and monitoring plan.
>
> This format mirrors how senior fraud managers communicate program evolution to
> executives and risk governance stakeholders. It proves that the program is governed
> by deliberate, defensible choices rather than ad-hoc engineering.
>
> **Audience:** Fraud Operations, Risk Governance, Product, Engineering, Legal.

***

## Decision Log Format

Each entry follows this structure:

```
Decision ID:    DL-XXX
Date:           YYYY-QX
Status:         Active / Superseded / Under Review
Problem:        What business or operational problem prompted this decision?
Options:        What alternatives were considered?
Decision:       What was chosen?
Reason:         Why was this option selected?
Expected Impact: Quantified or described expected outcome.
FP Impact:      Expected false-positive effect.
Owner:          Who owns this decision and its monitoring?
Monitoring:     How will the outcome be tracked?
```

***

## DL-001 — Scoring Engine: Weighted Blend vs. Decision Matrix

**Decision ID:** DL-001
**Date:** Q1 2025
**Status:** Under Review (v2 planned for Q3 2025)

**Problem:**
Initial Sentinel design used a fixed percentage blend for ensemble scoring
(XGBoost 45%, Isolation Forest 25%, SQL signals 20%, Graph 10%). Operational
review identified a structural weakness: a Fatal-tier SQL signal (e.g., impossible
physical transit) could be buffered by a low ML score, resulting in a CRITICAL
rather than FATAL routing. This creates legal exposure if a clearly impossible
event is treated as ambiguous.

**Options considered:**
- **Option A:** Keep weighted blend, increase SQL weight to 40%.
  *Risk: Still dilutes hard rules with probabilistic scores.*
- **Option B:** Implement a severity-tiered decision matrix. Fatal rules override
  ensemble. ML+graph rank within the gray band.
  *Risk: More complex to implement; requires tier definition for all 25 signals.*
- **Option C:** Use weighted blend for v1; revert to matrix in v2 after signal tiers are validated.
  *Risk: Defers the structural fix.*

**Decision:** Option C (v1 weighted blend; v2 decision matrix).

**Reason:**
Weighted blend is acceptable for portfolio demonstration and provides a baseline
from which tier performance can be estimated. Decision matrix is architecturally
correct for production but requires empirical signal-tier validation before
threshold-setting. Prioritized shipping a coherent v1 over a theoretically correct
but unvalidated v2.

**Expected impact:**
- v1: Functional detection with known limitation documented.
- v2: 15–25% improvement in Fatal-tier routing precision (modeled assumption).

**FP impact:** Neutral in v1. Decision matrix expected to reduce FP rate by 8–12%
in v2 by preventing gray-area ML scores from inflating Fatal signals.

**Owner:** Data Science + Fraud Operations Lead.

**Monitoring:** Track Fatal-tier routing accuracy monthly. If >10% of Fatal-tier
cases are scoring below CRITICAL due to low ML score, accelerate v2 timeline.

***

## DL-002 — CRITICAL Queue Cap: 25 Cases per Run

**Decision ID:** DL-002
**Date:** Q1 2025
**Status:** Active

**Problem:**
Sentinel generates risk scores for all flagged drivers in each run. Without a
queue cap, the CRITICAL case generation volume would exceed realistic investigator
capacity, diluting urgency and creating a false sense of program scale. A model
that generates 2,000 CRITICAL cases per day for a team of 10 investigators is
operationally non-functional.

**Options considered:**
- **Option A:** No cap; generate all CRITICAL cases. Investigators prioritize by score.
  *Risk: Queue bloat; urgency dilution; investigator overload.*
- **Option B:** Cap at 25 per run. Overflow held for next cycle.
  *Risk: Some high-risk cases may be delayed by one cycle.*
- **Option C:** Dynamic cap based on investigator headcount input parameter.
  *Risk: More complex; headcount variable not always known at runtime.*

**Decision:** Option B (fixed cap of 25).

**Reason:**
25 cases represents a realistic single-investigator daily capacity at 12–18 minutes
per case with a standard 8-hour shift. The cap is a deliberate modeling of operational
reality, not a technical constraint. Overflow cases are preserved and ranked; the
highest-scoring overflow cases surface first in the next cycle.

**Expected impact:**
- Maintains investigator productivity and case quality.
- Prevents urgency dilution from queue bloat.
- Models realistic ROI: 25 cases × 88% precision × avg fraud loss = bounded, defensible daily prevention estimate.

**FP impact:** Cap reduces total daily FP volume proportionally. FP rate (as a fraction) unchanged.

**Owner:** Fraud Operations Lead.

**Monitoring:** Track overflow queue depth weekly. If overflow consistently exceeds
100 cases, evaluate whether cap increase or investigator headcount increase is warranted.

***

## DL-003 — Evidence Integrity: SHA-256 Case File Hashing

**Decision ID:** DL-003
**Date:** Q1 2025
**Status:** Active

**Problem:**
Fraud case files are Markdown documents stored in a Git repository. Without
integrity verification, there is no way to prove that a case file was not altered
after generation — a potential legal liability if adverse actions are challenged.

**Options considered:**
- **Option A:** No integrity verification. Rely on Git history.
  *Risk: Git history can be rewritten; not audit-grade.*
- **Option B:** SHA-256 hash of each case file written at generation time; hash
  embedded in the file and stored separately in an index.
  *Risk: Minimal; slight increase in generation time.*
- **Option C:** External evidence management system (e.g., enterprise forensic tool).
  *Risk: Overkill for portfolio scope; not available in demo environment.*

**Decision:** Option B (SHA-256 hash chain).

**Reason:**
SHA-256 provides cryptographic integrity verification that Git alone cannot guarantee.
Embedding the hash in the case file and recording it in a separate index allows
any investigator or auditor to verify that the evidence was not altered after generation.
This directly addresses Legal's requirement for defensible adverse-action documentation.

**Expected impact:**
- Every case file can be verified as unaltered at any point in its lifecycle.
- Legal can confidently use case files as evidence in contractor disputes.

**FP impact:** None.

**Owner:** Detection Engineering.

**Monitoring:** Hash verification run on quarterly audit sample. Any mismatch triggers
immediate security review.

***

## DL-004 — GPS Spoofing Response: Threshold vs. Device Attestation

**Decision ID:** DL-004
**Date:** Q2 2025
**Status:** Active

**Problem:**
GPS spoofing incidents increased approximately 31% month-over-month during a
high-incentive promotion window. Two response options were evaluated.

**Options considered:**
- **Option A:** Tighten impossible transit threshold (lower speed threshold from 120mph to 80mph).
  *Pro: Fast to implement. Con: Higher FP rate; legitimate GPS edge cases more likely to trigger.*
- **Option B:** Require device attestation (Play Integrity API / Apple DeviceCheck)
  at delivery confirmation for drivers with ≥ 2 prior geofence anomalies.
  *Pro: Structurally addresses root cause; lower FP rate. Con: Medium engineering effort; adds friction for some legitimate drivers.*
- **Option C:** Delay payout 24h for all trips from flagged devices.
  *Pro: Buys investigation time. Con: High contractor friction; disproportionate for low-risk drivers.*

**Decision:** Option B — Device attestation for flagged drivers.

**Reason:**
Option B addresses the root cause (compromised device integrity) rather than
tightening a threshold that creates FP risk for legitimate drivers. The friction
is proportionate (only applies to drivers with prior anomalies) and preserves
the experience for the majority of legitimate contractors. Option C was rejected
as disproportionate.

**Expected impact:**
- Reduce confirmed GPS spoofing without applying device-attestation friction to the
  full driver population.
- Quantify impact only after a controlled rollout with adjudicated outcomes.

**FP impact:** Monitor added friction for legitimate drivers with prior geofence anomalies.
Mitigate through fast-track attestation review and an appeal process.

**Owner:** Fraud Operations + Platform Integrity Engineering.

**Monitoring:** Weekly spoof rate by device attestation status.
Alert if FP rate among attested drivers exceeds 3%.

***

## DL-005 — OSINT Layer: Full Vendor Integration vs. Simulated Enrichment

**Decision ID:** DL-005
**Date:** Q1 2025
**Status:** Active (Portfolio scope)

**Problem:**
The OSINT enrichment layer requires access to commercial identity verification,
device intelligence, and address verification vendors. In a production deployment,
these would be live API integrations. In a portfolio project using synthetic data,
live vendor calls are not possible.

**Options considered:**
- **Option A:** Build OSINT module with simulated enrichment only; no vendor references.
  *Risk: Looks theoretical; doesn't demonstrate vendor ecosystem knowledge.*
- **Option B:** Build OSINT module with simulated enrichment AND explicit documentation
  of production vendor equivalents for each enrichment type.
  *Pro: Demonstrates vendor landscape knowledge; clearly scoped to portfolio context.*
- **Option C:** Skip OSINT entirely; focus on signal and ML layers only.
  *Risk: Loses a significant differentiator; investigation workflow is incomplete without enrichment.*

**Decision:** Option B — Simulated enrichment with documented vendor equivalents.

**Reason:**
Option B preserves the architectural completeness of the investigation workflow
while being transparent about the portfolio scope. Naming production-equivalent
vendors (Socure, Incognia, SEON, LexisNexis, Sentilink, Persona) demonstrates
vendor ecosystem knowledge that is directly relevant to enterprise fraud operations.
No false claims of live integration are made.

**Expected impact:**
- Portfolio reviewers understand both the system design and the real-world
  vendor landscape it models.
- OSINT layer remains a meaningful differentiator vs. model-only portfolios.

**FP impact:** None.

**Owner:** Detection Engineering + Fraud Operations.

**Monitoring:** N/A (portfolio scope). In production deployment, OSINT enrichment
vendor SLA and API error rate would be monitored weekly.

***

## DL-006 — Confidence Levels: Binary Fraud Flag vs. Graduated Confidence Bands

**Decision ID:** DL-006
**Date:** Q1 2025
**Status:** Active

**Problem:**
Early design used a binary fraud/not-fraud output. This is common in academic
fraud models but operationally problematic: it forces a hard decision on cases
that should be monitored or investigated further, and it creates adverse-action
risk for borderline cases.

**Options considered:**
- **Option A:** Binary output (Fraud / Not Fraud).
  *Risk: Oversimplifies case routing; creates FP and legal exposure.*
- **Option B:** Five-band confidence system (Low / Medium / High / Critical / Fatal)
  with defined operational responses for each band.
  *Pro: Matches how real fraud operations teams route cases; proportionate to evidence strength.*
- **Option C:** Continuous 0–10 score only; let investigators use judgment.
  *Risk: Inconsistent investigator decisions; no documented routing standard.*

**Decision:** Option B — Five-band confidence system.

**Reason:**
Graduated confidence bands directly map to investigative workflow: different bands
trigger different actions, different analyst time commitments, and different approval
requirements. This is how enterprise fraud platforms (Unit21, Actimize, Pega) route
cases. The continuous score is preserved for ranking within bands.

**Expected impact:**
- Investigator time is allocated proportionately to evidence strength.
- Adverse action risk is reduced by requiring higher evidence standards for higher-severity actions.
- Program is defensible to Legal: every action tier has a documented evidence standard.

**FP impact:** Graduated bands reduce FP-driven adverse actions by requiring multi-signal
corroboration before Critical or Fatal routing.

**Owner:** Fraud Operations + Data Science.

**Monitoring:** Monthly review of case distribution across confidence bands.
Alert if >30% of scored drivers fall into High or above (may indicate threshold needs recalibration).
