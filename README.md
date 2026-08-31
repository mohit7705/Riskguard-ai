# RiskGuard AI

> AI-powered return-abuse detection and risk-management platform for e-commerce merchants.

RiskGuard AI is an end-to-end machine-learning system that identifies suspicious
return behavior, quantifies risk, routes cases to the appropriate business
action, and supports human analysts during investigation.

It combines machine-learning risk prediction, explainable risk signals,
network analysis, business decisioning, and human-in-the-loop review into a
single operational workflow.

**Core pipeline:**

```
Return Data
     ↓
Feature Engineering
     ↓
ML Risk Prediction (Calibrated XGBoost)
     ↓
Risk Score (0–100) + Risk Level
     ↓
Explainable Risk Signals (native XGBoost TreeSHAP)
     ↓
Business Decision (ALLOW / REVIEW / BLOCK)
     ↓
Human-in-the-Loop Review (when required)
     ↓
Feedback & Monitoring
```

---

## Table of Contents

1. [Problem](#1-problem)
2. [Key Features](#2-key-features)
3. [Machine Learning](#3-machine-learning)
4. [Dataset](#4-dataset)
5. [Feature Engineering](#5-feature-engineering)
6. [Model Evaluation](#6-model-evaluation)
7. [Threshold Optimization](#7-threshold-optimization)
8. [Financial Impact](#8-financial-impact)
9. [Backend API](#9-backend-api)
10. [Frontend](#10-frontend)
11. [Technology Stack](#11-technology-stack)
12. [Project Structure](#12-project-structure)
13. [Running the Backend](#13-running-the-backend)
14. [Running the Frontend](#14-running-the-frontend)
15. [Production Build](#15-production-build)
16. [Validation](#16-validation)
17. [Example Prediction](#17-example-prediction)
18. [Design Principles](#18-design-principles)
19. [Current Limitations](#19-current-limitations)
20. [Hackathon Context](#20-hackathon-context)
21. [License](#21-license)

---

## 1. Problem

E-commerce return abuse creates significant financial losses and operational overhead. Common patterns include:

- Repeated or serial returns
- Wardrobing (using an item, then returning it)
- Item swapping or empty-box returns
- Suspicious account behavior on new or thin-history accounts
- Coordinated abuse across linked accounts (shared devices, addresses, or payment methods)

A simple binary classifier is not sufficient for an operational risk system — a merchant needs to know not just *whether* a return is risky, but *how* risky, *why*, and *what to do about it*. RiskGuard AI converts a model prediction into an actionable risk-management workflow, ending in either an automated decision or a routed human review.

---

## 2. Key Features

### Return Risk Scoring

Each return request is evaluated using behavioral, transactional, account, package, and network-related signals. The model outputs:

- Abuse probability and legitimate probability
- Risk score (0–100)
- Risk level (MINIMAL / LOW / MEDIUM / HIGH / CRITICAL)
- Business decision and recommended action
- Top contributing risk signals for this specific case

### Business Decision Engine

Predictions are translated into operational decisions:

| Decision | Action |
|---|---|
| ALLOW | ALLOW_RETURN |
| REVIEW | MANUAL_REVIEW |
| BLOCK | BLOCK_RETURN |

Medium- and high-risk cases are routed to the human review workflow rather than being auto-blocked.

### Human-in-the-Loop (HITL) Review

Analysts work through a review queue where they can inspect the model's prediction, risk score, abuse probability, contributing signals, and the original return data, then submit a decision with a mandatory reason.

Supported analyst decisions: **ALLOW**, **BLOCK**

Case lifecycle:

```
OPEN → Analyst Investigation → ALLOW / BLOCK → RESOLVED
```

### Explainable Risk Signals

Each prediction includes the features that most contributed to that specific case's risk assessment — not a generic model-wide ranking, but a per-case explanation. See [Model Evaluation](#6-model-evaluation) and the note under [Design Principles](#18-design-principles) for how this is computed.

### Abuse-Ring Network Analysis

RiskGuard AI can trace relationships between accounts through shared identifiers — devices, addresses, and payment fingerprints — to surface coordinated abuse that a single-return view would miss:

```
              Device
             /      \
        User A      User B
          |            |
       Address      Payment
          |            |
        User C      User D
```

The API exposes this as a graph (nodes, edges) plus network-level summary statistics (shared counts, return velocity across the cluster).

### Bulk Assessment

Supports both CSV upload and developer JSON input for evaluating multiple return requests in a single batch, returning an individual decision for every record.

### Risk Reporting

The reporting dashboard provides a merchant-facing view of the whole system: total reviewed returns, pending review count, allowed/blocked counts, abuse rate, risk distribution, decision trends, top return reasons, model performance, threshold trade-off analysis, and financial impact — all backed by live data, not static mockups.

---

## 3. Machine Learning

The production inference model is a **calibrated XGBoost classifier**.

| Property | Value |
|---|---|
| Model | CalibratedXGBClassifier |
| Feature count | 34 |
| Classes | 0 (Legitimate), 1 (Abusive) |

Calibration matters here specifically because raw gradient-boosted probabilities are often poorly calibrated — without it, a "70% abuse probability" wouldn't reliably mean what it says, which would undermine both the risk-score display and the cost-based threshold selection described in [Section 7](#7-threshold-optimization).

A Random Forest baseline was trained alongside XGBoost for comparison; XGBoost was selected for production based on stronger ROC-AUC and F1 on the same held-out test set.

---

## 4. Dataset

RiskGuard AI uses a controlled synthetic return-abuse dataset. The generation pipeline creates users, orders, order items, returns, behavioral features, network/linkage features, and abuse labels, with validation checks performed before the training data is persisted.

Controlled abuse categories represented in the synthetic data:

- WARDROBING
- ITEM_SWAP_OR_EMPTY_BOX
- ABUSE_RING
- SUSPICIOUS_ACCOUNT_BEHAVIOR
- SERIAL_RETURNER

---

## 5. Feature Engineering

34 model features span five categories: transactional, behavioral, account, return/package, and network-related. Representative examples:

```
order_value                          return_velocity_30d
item_value                           return_velocity_48h
quantity                             shared_device_count
time_to_return_request_hours         shared_address_count
refund_amount                        shared_payment_fingerprint_count
returned_item_match                  device_return_velocity_7d
item_condition_score                 address_return_velocity_7d
package_weight_delta_pct             payment_return_velocity_7d
vision_confidence_score              cluster_return_velocity_7d
account_age_days
lifetime_order_count
lifetime_return_count
total_spent
return_rate
```

Categorical fields (`order_category`, `return_reason`) are one-hot encoded consistently between training and inference.

---

## 6. Model Evaluation

Evaluated on a held-out test set of **2,000 rows**, at the production decision threshold of **0.70**:

| Metric | Score |
|---|---|
| Precision | 96.38% |
| Recall | 99.75% |
| F1 Score | 98.03% |
| PR-AUC | 99.42% |
| ROC-AUC | 99.87% |

**Confusion matrix:**

| | Predicted Legitimate | Predicted Abusive |
|---|---|---|
| **Actual Legitimate** | 1585 | 15 |
| **Actual Abusive** | 1 | 399 |

| | Count |
|---|---|
| True Positives | 399 |
| True Negatives | 1585 |
| False Positives | 15 |
| False Negatives | 1 |

These are real numbers computed on held-out data, not spot checks — every threshold in [Section 7](#7-threshold-optimization) was evaluated against this same test set.

---

## 7. Threshold Optimization

Rather than using the default 0.5 cutoff, RiskGuard AI selects its decision threshold by evaluating multiple candidate thresholds against an explicit business-cost function — because in return-abuse detection, a false positive (blocking a genuine customer) and a false negative (missing real abuse) do not cost the same thing.

**Cost assumptions:**

```
False Positive Cost = 1
False Negative Cost = 5
```

**Cost formula:**

```
Business Cost = (False Positives × FP Cost) + (False Negatives × FN Cost)
```

The threshold minimizing this cost across 17 tested values (0.10–0.90) is selected automatically. Currently:

| Threshold | False Positives | False Negatives | Business Cost |
|---|---|---|---|
| **0.70 (selected)** | 15 | 1 | **20** |

This full threshold sweep — every candidate value with its precision, recall, F1, and cost — is persisted to `backend/ml/models/risk_threshold_report.json` and surfaced live on the Report dashboard as a threshold-vs-cost tradeoff chart, so the choice of 0.70 is auditable rather than asserted. The same threshold is loaded into the production model bundle and returned as `decision_threshold` on every prediction, so the API's live decisions and the dashboard's reported metrics are guaranteed to reflect the same cutoff.

---

## 8. Financial Impact

RiskGuard AI deliberately distinguishes between **observed exposure** and **realized savings** — these are not the same thing, and conflating them would overstate the system's proven impact.

**Held-out test set analysis:**

| Metric | Value |
|---|---|
| Potential refund exposure identified | ₹49,015.25 |
| Observed missed refund exposure | ₹315.31 |
| Observed fraud-exposure reduction | ₹48,699.94 |

> **Important:** Detected-abuse amounts represent *potential prevented exposure*, not realized savings. False-positive friction is currently represented as a normalized cost unit rather than a rupee amount, since that conversion depends on merchant-specific assumptions (support cost, churn probability) not yet supplied.

---

## 9. Backend API

Built with **FastAPI**. Interactive documentation available at `http://127.0.0.1:8000/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/risk/predict` | Single return risk prediction |
| POST | `/api/v1/risk/predict/batch` | Batch risk prediction |
| GET | `/api/v1/risk/review-queue` | List open review cases |
| GET | `/api/v1/risk/review-queue/{case_id}` | Get one review case |
| POST | `/api/v1/risk/review-queue/{case_id}/decision` | Submit analyst decision |
| GET | `/api/v1/risk/feedback` | List feedback records |
| GET | `/api/v1/risk/feedback/{feedback_id}` | Get one feedback record |
| POST | `/api/v1/risk/feedback/{feedback_id}/outcome` | Record actual outcome |
| GET | `/api/v1/risk/monitoring` | Model monitoring metrics |
| GET | `/api/v1/risk/network/{user_id}` | Network/linkage analysis |
| GET | `/api/v1/report/dashboard` | Reporting dashboard data |
| GET | `/health` | Service health check |

---

## 10. Frontend

Built with **React, TypeScript, Vite, Recharts, and Lucide React**.

| Page | Capabilities |
|---|---|
| **Report** | KPI cards, risk distribution, decision trends, top risk reasons, model performance, financial impact, threshold tradeoff chart, review queue |
| **Single Assessment** | Guided form (grouped, labeled fields) or raw developer JSON, live risk assessment, decision + risk signals |
| **Bulk Assessment** | CSV upload or developer JSON, batch summary, per-record decisions |
| **Network Analysis** | Enter a user ID, inspect connected users/devices/addresses/payment fingerprints |

---

## 11. Technology Stack

**Backend:** Python 3.10, FastAPI, SQLAlchemy, PostgreSQL, Pydantic, Uvicorn

**Machine Learning:** Scikit-learn, XGBoost, Pandas, NumPy, Joblib

**Frontend:** React, TypeScript, Vite, Recharts, Lucide React

**Development:** uv, Git

---

## 12. Project Structure

```
RiskGuard AI/
│
├── backend/
│   ├── app/
│   │   ├── db/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── ml/
│   │   ├── data/
│   │   │   ├── features/
│   │   │   ├── generators/
│   │   │   └── validators/
│   │   ├── decision/
│   │   ├── inference/
│   │   ├── models/
│   │   └── training/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── data/
├── notebooks/
├── docs/
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

---

## 13. Running the Backend

From the project root:

```bash
uv sync
uv run uvicorn backend.app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

---

## 14. Running the Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will print the local frontend URL.

---

## 15. Production Build

```bash
cd frontend
npm run build
```

Successfully compiles with TypeScript project references and a Vite production build.

---

## 16. Validation

**API Validation:** missing request data, invalid data types, empty-body rejection, single and batch prediction round-trips.

**ML Validation:** held-out test-set evaluation (precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix), threshold optimization against a business-cost function, financial exposure analysis.

**HITL Validation:** review-queue retrieval, individual case lookup, analyst decision submission, case resolution lifecycle.

**System Validation:** backend health check, Swagger/OpenAPI availability, report dashboard API, network API, review queue API, frontend production build, end-to-end API smoke tests.

---

## 17. Example Prediction

```json
{
  "prediction": "ABUSIVE",
  "abuse_probability": 0.969667,
  "legitimate_probability": 0.030333,
  "risk_score": 96.97,
  "risk_level": "CRITICAL",
  "decision": "BLOCK",
  "action": "BLOCK_RETURN",
  "decision_threshold": 0.70
}
```

---

## 18. Design Principles

**Explainability** — A risk decision should come with understandable, per-case contributing signals, not just a number. RiskGuard AI computes these using XGBoost's native TreeSHAP (`Booster.predict(..., pred_contribs=True)`) rather than the third-party `shap` package, due to a confirmed upstream incompatibility between `shap`'s TreeExplainer and XGBoost's newer `base_score` serialization format (tracked upstream as `shap/shap#4288`). XGBoost implements the identical TreeSHAP algorithm natively in C++, so this produces mathematically equivalent per-feature Shapley values without depending on the broken loader. If no usable booster can be recovered from the model bundle, the system falls back to static global feature importance rather than failing the request.

**Human Oversight** — Medium- and high-risk cases are escalated to human analysts rather than auto-blocked.

**Business-Aware Risk** — The system optimizes its decision threshold against an explicit false-positive/false-negative cost function, not raw accuracy alone.

**Network Intelligence** — Abuse frequently spans multiple accounts, so shared-device, address, payment, and velocity features are first-class inputs, not an afterthought.

**Defense-Oriented Workflow** — The system is built for detection, investigation, and prevention — not for autonomous offensive action of any kind.

---

## 19. Current Limitations

This is a hackathon project and should not be interpreted as a production fraud engine without further validation. Specifically:

- The training dataset is synthetic.
- Reported financial figures are exposure/estimate measurements, not realized savings.
- False-positive friction is currently a normalized unit rather than a calibrated rupee cost, pending real merchant-specific assumptions.
- Per-case explainability depends on a recoverable XGBoost booster inside the loaded model bundle; if none is found, the system falls back to static global feature importance for that request.
- Production deployment, authentication, monitoring infrastructure, and real merchant integrations would require additional engineering.
- Real-world calibration would require validated production outcomes, not synthetic labels.

---

## 20. Hackathon Context

RiskGuard AI was built as an AI-powered risk-management solution focused on return-abuse detection, structured around one idea:

```
Detect → Score → Explain → Decide → Review → Learn
```

The goal is not simply to classify a return as fraudulent. The goal is to give merchants an operational risk-management system that identifies suspicious behavior, explains *why* it's suspicious, quantifies the business impact of that decision, and routes it to the right outcome — automated or human — accordingly.

---

## 21. License

This project is intended for hackathon, demonstration, and educational purposes. Add an appropriate license before any commercial distribution.
