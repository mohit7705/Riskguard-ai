import {
  Target,
  Percent,
  BarChart3,
  Activity,
  ShieldCheck,
  IndianRupee,
} from "lucide-react";
import type {
  ModelPerformance,
  FinancialImpact,
} from "../api/report";

type Props = {
  performance?: ModelPerformance;
  impact?: FinancialImpact;
};

function formatPct(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatInr(value: number) {
  return `₹${value.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  })}`;
}

function ModelInsights({ performance, impact }: Props) {
  if (!performance && !impact) {
    return null;
  }

  return (
    <div className="model-insights">
      {performance && (
        <div className="chart-card model-perf-card">
          <div className="model-perf-header">
            <h3>Model Performance</h3>

            <span className="model-perf-meta">
              {performance.model} · {performance.test_rows}{" "}
              held-out rows · threshold {performance.threshold}
            </span>
          </div>

          <div className="perf-metric-grid">
            <div className="perf-metric">
              <Target size={16} strokeWidth={2.2} />
              <span>Precision</span>
              <strong>{formatPct(performance.precision)}</strong>
            </div>

            <div className="perf-metric">
              <Percent size={16} strokeWidth={2.2} />
              <span>Recall</span>
              <strong>{formatPct(performance.recall)}</strong>
            </div>

            <div className="perf-metric">
              <Activity size={16} strokeWidth={2.2} />
              <span>F1 Score</span>
              <strong>{formatPct(performance.f1_score)}</strong>
            </div>

            <div className="perf-metric">
              <BarChart3 size={16} strokeWidth={2.2} />
              <span>PR-AUC</span>
              <strong>{formatPct(performance.pr_auc)}</strong>
            </div>

            <div className="perf-metric">
              <ShieldCheck size={16} strokeWidth={2.2} />
              <span>ROC-AUC</span>
              <strong>{formatPct(performance.roc_auc)}</strong>
            </div>
          </div>

          <div className="confusion-matrix">
            <div className="confusion-cell confusion-tp">
              <span>True Positives</span>
              <strong>{performance.true_positives}</strong>
            </div>

            <div className="confusion-cell confusion-fn">
              <span>False Negatives</span>
              <strong>{performance.false_negatives}</strong>
            </div>

            <div className="confusion-cell confusion-fp">
              <span>False Positives</span>
              <strong>{performance.false_positives}</strong>
            </div>

            <div className="confusion-cell confusion-tn">
              <span>True Negatives</span>
              <strong>{performance.true_negatives}</strong>
            </div>
          </div>
        </div>
      )}

      {impact && (
        <div className="chart-card financial-impact-card">
          <h3>Financial Impact</h3>

          <div className="impact-row">
            <div className="impact-icon blue">
              <IndianRupee size={18} strokeWidth={2.2} />
            </div>

            <div>
              <span>Potential Refund Exposure Identified</span>
              <strong>
                {formatInr(
                  impact.potential_refund_exposure_identified_inr,
                )}
              </strong>
            </div>
          </div>

          <div className="impact-row">
            <div className="impact-icon green">
              <IndianRupee size={18} strokeWidth={2.2} />
            </div>

            <div>
              <span>Fraud Exposure Reduction</span>
              <strong>
                {formatInr(
                  impact.observed_fraud_exposure_reduction_inr,
                )}
              </strong>
            </div>
          </div>

          <div className="impact-row">
            <div className="impact-icon red">
              <IndianRupee size={18} strokeWidth={2.2} />
            </div>

            <div>
              <span>Missed Refund Exposure</span>
              <strong>
                {formatInr(
                  impact.observed_missed_refund_exposure_inr,
                )}
              </strong>
            </div>
          </div>

          <div className="impact-row">
            <div className="impact-icon amber">
              <IndianRupee size={18} strokeWidth={2.2} />
            </div>

            <div>
              <span>
                False-Positive Friction Cost (
                {impact.false_positive_friction_cost_unit})
              </span>
              <strong>
                {impact.false_positive_friction_cost}
              </strong>
            </div>
          </div>

          <p className="impact-disclaimer">
            {impact.financial_interpretation}
          </p>
        </div>
      )}
    </div>
  );
}

export default ModelInsights;
