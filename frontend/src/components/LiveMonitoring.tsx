import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Target,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  getMonitoringMetrics,
  type MonitoringResponse,
} from "../api/risk";

function formatMetric(value: number | null) {
  if (value === null) {
    return "N/A";
  }

  return `${(value * 100).toFixed(2)}%`;
}

function LiveMonitoring() {
  const [metrics, setMetrics] = useState<MonitoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      const data = await getMonitoringMetrics();
      setMetrics(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load monitoring metrics",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  return (
    <section className="monitoring-section">
      <div className="section-heading">
        <div>
          <p className="section-eyebrow">PRODUCTION FEEDBACK</p>
          <h2>Production Feedback Monitoring</h2>
        </div>

        <button
          type="button"
          className="monitoring-refresh-button"
          onClick={() => void loadMetrics(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? "spin" : ""}
          />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="monitoring-error">
          <AlertTriangle size={17} />
          <span>{error}</span>
        </div>
      )}

      <div className="monitoring-card">
        <div className="monitoring-status">
          <div className="monitoring-status-icon">
            <Activity size={18} />
          </div>

          <div>
            <strong>Feedback monitoring</strong>
            <span>
              Metrics calculated from labeled production outcomes
            </span>
          </div>
        </div>

        <div className="monitoring-grid">
          <div className="monitoring-metric">
            <Activity size={16} />
            <span>Total Predictions</span>
            <strong>
              {loading ? "—" : metrics?.total_records.toLocaleString("en-IN")}
            </strong>
          </div>

          <div className="monitoring-metric">
            <Target size={16} />
            <span>Labeled Outcomes</span>
            <strong>
              {loading
                ? "—"
                : metrics?.labeled_records.toLocaleString("en-IN")}
            </strong>
          </div>

          <div className="monitoring-metric">
            <CheckCircle2 size={16} />
            <span>Accuracy</span>
            <strong>
              {loading ? "—" : formatMetric(metrics?.accuracy ?? null)}
            </strong>
          </div>

          <div className="monitoring-metric">
            <Target size={16} />
            <span>Precision</span>
            <strong>
              {loading ? "—" : formatMetric(metrics?.precision ?? null)}
            </strong>
          </div>

          <div className="monitoring-metric">
            <Activity size={16} />
            <span>Recall</span>
            <strong>
              {loading ? "—" : formatMetric(metrics?.recall ?? null)}
            </strong>
          </div>

          <div className="monitoring-metric">
            <Target size={16} />
            <span>F1 Score</span>
            <strong>
              {loading ? "—" : formatMetric(metrics?.f1_score ?? null)}
            </strong>
          </div>
        </div>

        <div className="monitoring-outcomes">
          <div>
            <span>
              <XCircle size={14} />
              False Positives
            </span>
            <strong>{loading ? "—" : metrics?.false_positive_count}</strong>
          </div>

          <div>
            <span>
              <AlertTriangle size={14} />
              False Negatives
            </span>
            <strong>{loading ? "—" : metrics?.false_negative_count}</strong>
          </div>

          <div>
            <span>True Positives</span>
            <strong>{loading ? "—" : metrics?.true_positive_count}</strong>
          </div>

          <div>
            <span>True Negatives</span>
            <strong>{loading ? "—" : metrics?.true_negative_count}</strong>
          </div>

          <div>
            <span>Business Cost</span>
            <strong>
              {loading
                ? "—"
                : metrics?.business_cost.toFixed(2)}
            </strong>
          </div>
        </div>

        {!loading && metrics?.labeled_records === 0 && (
          <p className="monitoring-note">
            No actual outcomes have been labeled yet. Production
            performance metrics will appear as analyst or downstream
            outcomes are recorded.
          </p>
        )}
      </div>
    </section>
  );
}

export default LiveMonitoring;
