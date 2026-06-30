# Incident Response Playbook
## Project Sentinel — Mass Fraud Event Escalation

**Owner:** Trust Intelligence Program Lead  
**Last reviewed:** 2026-06-29  
**Review cadence:** Quarterly, or after any Severity-1 incident  
**Distribution:** Trust, Legal, Finance, Engineering, Executive

---

## Purpose

This playbook governs the coordinated response when Sentinel detects or confirms a mass fraud event — defined as a coordinated pattern affecting 10 or more contractors simultaneously, or any single-run detection that flags a total estimated loss above **$50,000**.

It answers three questions every responder needs immediately:

1. Who is notified, in what order, and on what timeline?
2. Who has authority to take which actions?
3. What is the evidence standard before each action?

---

## Severity Classification

| Severity | Trigger | Example |
|----------|---------|---------|
| **SEV-1 (Critical)** | 50+ contractors in a coordinated ring OR estimated loss > $250K in one settlement cycle | GPS-spoofing ring across 3 cities, 80 contractors |
| **SEV-2 (High)** | 10-49 contractors OR estimated loss $50K-$250K | Shared-payout cluster, 22 contractors |
| **SEV-3 (Elevated)** | Novel signal pattern with no confirmed loss yet | New emulator fingerprint, 30 flagged accounts |

Sentinel auto-generates a SEV classification based on composite score band distribution and ring size.

---

## Notification Chain

### SEV-1

| Time | Action | Owner |
|------|--------|-------|
| T+0 | Sentinel CRITICAL+ batch detected | Automated (run.py output) |
| T+15 min | Trust Program Lead paged | On-call rotation |
| T+30 min | Trust Program Lead confirms SEV-1, notifies VP Trust & Safety | Trust Program Lead |
| T+45 min | VP Trust & Safety notifies General Counsel and CFO | VP Trust & Safety |
| T+1 hr | War-room channel opened | Trust Program Lead |
| T+2 hr | Engineering Lead joins to assess streaming pipeline options | VP Trust & Safety |
| T+4 hr | Executive status update to CEO if estimated loss > $500K | General Counsel |

### SEV-2

| Time | Action | Owner |
|------|--------|-------|
| T+0 | Sentinel batch detected | Automated |
| T+1 hr | Trust Program Lead notified (async) | On-call rotation |
| T+4 hr | Trust Program Lead reviews and confirms classification | Trust Program Lead |
| T+8 hr | VP Trust & Safety briefed | Trust Program Lead |
| T+24 hr | Written summary to Legal | Trust Program Lead |

### SEV-3

Normal investigation queue. Trust Program Lead reviews next business day. No escalation unless classification upgrades.

---

## Decision Authority Matrix

| Action | Authority Required | Evidence Standard |
|--------|--------------------|-------------------|
| Individual CRITICAL — restrict (temporary) | Senior Investigator | CRITICAL+ score + 2 of 4 FP paths cleared |
| Individual — permanent deactivation | Trust Program Lead + Legal | CRITICAL+ score + all 4 FP paths cleared + OSINT confirmation |
| Mass restriction (10-49 accounts) | Trust Program Lead | Ring confirmed by graph + FP checklist completed for 3+ sampled accounts |
| Mass restriction (50+ accounts) | VP Trust & Safety + General Counsel | Ring confirmed + sampled FP rate < 10% across 5+ reviewed cases |
| Mass permanent deactivation | VP Trust & Safety + GC + CEO (if > 100) | Full SOP completed for 10%+ of ring members |
| Settlement hold | CFO + General Counsel | SEV-1 confirmed, estimated loss quantified |
| Law enforcement referral | General Counsel | SHA-256 evidence pack, OSINT verification, SHAP documentation |

---

## Mass Restriction Procedure

When authority is granted:

1. **Export ring membership list** from cases/ graph output — all contractor IDs with ring flag = 1 and composite score >= 7.0.
2. **Sample review** — Trust Program Lead reviews FP exclusion checklist for a random 10% sample (minimum 5 cases). If sampled FP rate > 10%, escalate before proceeding.
3. **Restriction batch** — Engineering applies temporary restrictions via contractor management API. Default 72-hour time-box requiring active extension.
4. **Notification** — Affected contractors receive automated 'account under review' notice. Do not disclose detection methodology.
5. **Appeals intake** — Trust opens expedited appeals queue within 1 hour of restriction batch.

---

## Evidence Preservation

For any SEV-1 or SEV-2 incident, immediately preserve:

- data/bronze/ Parquet files from the detection run (do not overwrite)
- All generated case files in cases/ for the run
- data/models/metrics.json from the run
- data/drift/alerts.jsonl if drift was flagged
- Raw OSINT enrichment outputs

SHA-256 lineage chain (data/bronze/lineage.json) is immutable by design. Do not modify. Preserve a copy in the incident record.

---

## Post-Incident Review

Within 5 business days of SEV-1 closure, or 10 business days of SEV-2:

- **Root cause:** How did the fraud pattern originate? Which product feature or incentive created the attack surface?
- **Detection lag:** How long between first fraudulent activity and CRITICAL flag?
- **False-positive audit:** Of all restricted accounts, what fraction were ultimately confirmed fraud? Document in DECISION_LOG.md.
- **Product recommendation:** Draft memo to Product identifying design changes to reduce fraud surface. Feed into INCENTIVE_INTEGRITY.md.
- **Signal update:** If a novel pattern was detected, draft the corresponding SQL signal for the library.

---

## Contact Directory

*(Replace with live on-call roster — stored separately from this document for security)*

| Role | Contact method |
|------|---------------|
| Trust Program Lead (primary) | On-call PagerDuty rotation |
| Trust Program Lead (backup) | On-call PagerDuty rotation |
| VP Trust & Safety | Mobile (stored in PagerDuty) |
| General Counsel | Mobile (stored in PagerDuty) |
| CFO | Mobile (stored in PagerDuty) |
| Engineering On-Call | PagerDuty |

---

*This playbook is version-controlled. Material changes require sign-off from Trust Program Lead and General Counsel before merge.*
