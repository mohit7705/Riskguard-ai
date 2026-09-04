import { useEffect, useState } from "react"
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Ban,
  ShieldAlert,
  Download,
} from "lucide-react"
import ReportCharts from "./ReportCharts"
import ModelInsights from "./ModelInsights"
import ThresholdCurve from "./ThresholdCurve"
import LiveMonitoring from "./LiveMonitoring"
import "./ReportDashboard.css"
import {
  getReportDashboard,
  type ReportDashboardResponse,
} from "../api/report"

function buildReportCsv(report: ReportDashboardResponse): string {
  const lines: string[] = [];

  const escape = (value: string | number) => {
    const str = String(value);
    if (str.includes(",") || str.includes('"')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const row = (...cells: (string | number)[]) =>
    lines.push(cells.map(escape).join(","));

  row("RiskGuard AI — Risk Report");
  row("Generated At", new Date().toISOString());
  row("");

  row("SUMMARY");
  row("Total Reviewed", report.summary.total_reviewed);
  row("Pending Review", report.summary.pending_review);
  row("Allowed", report.summary.allowed);
  row("Blocked", report.summary.blocked);
  row("Abuse Rate (%)", report.summary.abuse_rate);
  row("");

  row("RISK SCORE DISTRIBUTION");
  row("Level", "Count");
  Object.entries(report.risk_distribution).forEach(
    ([level, count]) => {
      row(level, count);
    },
  );
  row("");

  row("DECISIONS TREND");
  row("Date", "Allowed", "Blocked", "Review");

  report.decision_trend.forEach((point) => {
  row(point.date, point.allow, point.block, point.review);
  });

  row("");

  row("DAILY REPORT DATA");
  row("Date", "Total", "Allowed", "Blocked", "Review");

  report.daily_data.forEach((point) => {
  row(
    point.date,
    point.total,
    point.allowed,
    point.blocked,
    point.review,
  );
  });

  row("");
  row("TOP RISK REASONS");
  row("Reason", "Count");
  report.top_risk_reasons.forEach((item) => {
    row(item.reason, item.count);
  });
  row("");

  if (report.model_performance) {
    const perf = report.model_performance;
    row("MODEL PERFORMANCE");
    row("Model", perf.model);
    row("Test Rows", perf.test_rows);
    row("Threshold", perf.threshold);
    row("Precision", perf.precision);
    row("Recall", perf.recall);
    row("F1 Score", perf.f1_score);
    row("PR-AUC", perf.pr_auc);
    row("ROC-AUC", perf.roc_auc);
    row("True Positives", perf.true_positives);
    row("False Positives", perf.false_positives);
    row("True Negatives", perf.true_negatives);
    row("False Negatives", perf.false_negatives);
    row("");
  }

  if (report.threshold_curve) {
    const curve = report.threshold_curve;
    row("THRESHOLD SWEEP");
    row("Cost Formula", curve.cost_formula);
    row("Selected Threshold", curve.selected_threshold);
    row("Selection Reason", curve.selection_reason);
    row("");
    row(
      "Threshold",
      "Precision",
      "Recall",
      "F1",
      "False Positives",
      "False Negatives",
      "Business Cost",
    );
    curve.points.forEach((point) => {
      row(
        point.threshold,
        point.precision,
        point.recall,
        point.f1_score,
        point.false_positives,
        point.false_negatives,
        point.business_cost,
      );
    });
    row("");
  }

  if (report.financial_impact) {
    const impact = report.financial_impact;
    row("FINANCIAL IMPACT");
    row(
      "Potential Refund Exposure Identified (INR)",
      impact.potential_refund_exposure_identified_inr,
    );
    row(
      "Fraud Exposure Reduction (INR)",
      impact.observed_fraud_exposure_reduction_inr,
    );
    row(
      "Missed Refund Exposure (INR)",
      impact.observed_missed_refund_exposure_inr,
    );
    row(
      `False-Positive Friction Cost (${impact.false_positive_friction_cost_unit})`,
      impact.false_positive_friction_cost,
    );
    row("Note", impact.financial_interpretation);
  }

  return lines.join("\n");
}

function downloadCsv(filename: string, content: string) {
  const blob = new Blob([content], {
    type: "text/csv;charset=utf-8;",
  });

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

type ReviewFilter = 'all' | 'pending' | 'allowed' | 'blocked'

type ReportDashboardProps = {
  assignmentNumber: string
  onReviewFilter: (filter: ReviewFilter) => void
}

function ReportDashboard({
  assignmentNumber,
  onReviewFilter,
}: ReportDashboardProps) {
  const [report, setReport] =
    useState<ReportDashboardResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    async function loadReport() {
      try {
        const data = await getReportDashboard(assignmentNumber);
        setReport(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    loadReport();
  }, [assignmentNumber]);

  const handleExport = () => {
    if (!report) {
      return;
    }

    setExporting(true);

    try {
      const csv = buildReportCsv(report);

      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/[:T]/g, "-");

      downloadCsv(`riskguard-report-${timestamp}.csv`, csv);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div
      className={`report-dashboard ${loading ? "is-loading" : ""}`}
    >
      <div className="report-header">
        <div>
          <p className="eyebrow">REPORTING</p>

          <h1>Risk Reports</h1>

          <p className="report-subtitle">
            Review high-risk returns requiring analyst decisions.
          </p>
        </div>

        <button
          className="export-button"
          type="button"
          onClick={handleExport}
          disabled={!report || exporting}
        >
          <Download size={16} strokeWidth={2.5} />
          {exporting ? "Exporting..." : "Export Report"}
        </button>
      </div>

      <div className="report-cards">
        <div
          className="report-card"
          role="button"
          tabIndex={0}
          onClick={() => onReviewFilter('all')}
        >
          <div className="report-card-icon blue">
            <ShieldCheck size={20} strokeWidth={2.2} />
          </div>
          <div className="report-card-body">
            <span>Total Assessments</span>
            <h2>{report?.summary.total_reviewed ?? "-"}</h2>
          </div>
        </div>

        <div
          className="report-card"
          role="button"
          tabIndex={0}
          onClick={() => onReviewFilter('pending')}
        >
          <div className="report-card-icon amber">
            <AlertTriangle size={20} strokeWidth={2.2} />
          </div>
          <div className="report-card-body">
            <span>Pending Review</span>
            <h2>{report?.summary.pending_review ?? "-"}</h2>
          </div>
        </div>

        <div
          className="report-card"
          role="button"
          tabIndex={0}
          onClick={() => onReviewFilter('allowed')}
        >
          <div className="report-card-icon green">
            <CheckCircle2 size={20} strokeWidth={2.2} />
          </div>
          <div className="report-card-body">
            <span>Model Allowed</span>
            <h2>{report?.summary.allowed ?? "-"}</h2>
          </div>
        </div>

        <div
          className="report-card"
          role="button"
          tabIndex={0}
          onClick={() => onReviewFilter('blocked')}
        >
          <div className="report-card-icon red">
            <Ban size={20} strokeWidth={2.2} />
          </div>
          <div className="report-card-body">
            <span>Model Blocked</span>
            <h2>{report?.summary.blocked ?? "-"}</h2>
          </div>
        </div>

        <div className="report-card">
          <div className="report-card-icon purple">
            <ShieldAlert size={20} strokeWidth={2.2} />
          </div>
          <div className="report-card-body">
            <span>Abuse Rate</span>
            <h2>
              {report ? `${report.summary.abuse_rate}%` : "-"}
            </h2>
          </div>
        </div>
      </div>

      <div className="report-charts-wrap">
        <ReportCharts
          risk={report?.risk_distribution ?? {}}
          trend={report?.decision_trend ?? []}
          reasons={report?.top_risk_reasons ?? []}
        />
      </div>

      <LiveMonitoring assignmentNumber={assignmentNumber} />

      <ModelInsights
        performance={report?.model_performance}
        impact={report?.financial_impact}
      />

      <ThresholdCurve curve={report?.threshold_curve} />
    </div>
  );
}

export default ReportDashboard;