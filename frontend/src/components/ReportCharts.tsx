import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts";

type Props = {
  risk: {
    [key: string]: number;
  };

  trend: {
    date: string;
    allow: number;
    block: number;
    review: number;
  }[];

  reasons: {
    reason: string;
    count: number;
  }[];
};

const RISK_COLORS: Record<string, string> = {
  CRITICAL: "#c74646",
  HIGH: "#ef4444",
  MEDIUM: "#b7791f",
  LOW: "#198754",
  MINIMAL: "#3b82f6",
};

const FALLBACK_COLORS = [
  "#ef4444",
  "#b7791f",
  "#198754",
  "#3b82f6",
  "#8b5cf6",
];

const REASON_COLORS = [
  "#ef4444",
  "#f59e0b",
  "#eab308",
  "#22c55e",
  "#3b82f6",
  "#8b5cf6",
];

function ReportCharts({ risk, trend, reasons }: Props) {
  const riskEntries = Object.entries(risk);
  const riskTotal = riskEntries.reduce(
    (sum, [, value]) => sum + value,
    0,
  );

  const riskData = riskEntries.map(([name, value], index) => ({
    name,
    value,
    color:
      RISK_COLORS[name.toUpperCase()] ??
      FALLBACK_COLORS[index % FALLBACK_COLORS.length],
  }));

  const reasonsTotal = reasons.reduce(
    (sum, item) => sum + item.count,
    0,
  );

  const maxReasonCount = Math.max(
    1,
    ...reasons.map((item) => item.count),
  );

  return (
    <div className="report-charts">
      {/* Risk Score Distribution */}
      <div className="chart-card">
        <h3>Risk Score Distribution</h3>

        <div className="donut-wrap">
          <ResponsiveContainer width="100%" height={190}>
            <PieChart>
              <Pie
                data={riskData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={62}
                outerRadius={88}
                paddingAngle={2}
              >
                {riskData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>

              <Tooltip />
            </PieChart>
          </ResponsiveContainer>

          <div className="donut-center">
            <strong>{riskTotal}</strong>
            <span>Total</span>
          </div>
        </div>

        <div className="donut-legend">
          {riskData.map((entry) => (
            <div className="donut-legend-row" key={entry.name}>
              <span
                className="donut-dot"
                style={{ background: entry.color }}
              />

              <span className="legend-label">{entry.name}</span>

              <strong>{entry.value}</strong>

              <span className="legend-pct">
                (
                {riskTotal > 0
                  ? ((entry.value / riskTotal) * 100).toFixed(1)
                  : "0.0"}
                %)
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Decisions Trend */}
      <div className="chart-card">
        <h3>Decisions Trend</h3>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trend}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#eef1f5"
            />

            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: "#7b8798" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />

            <YAxis
              tick={{ fontSize: 12, fill: "#7b8798" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />

            <Tooltip />

            <Legend
              iconType="circle"
              wrapperStyle={{ fontSize: 13 }}
            />

            <Line
              dataKey="allow"
              name="Allowed"
              stroke="#198754"
              strokeWidth={2.5}
              dot={{ r: 3 }}
            />

            <Line
              dataKey="block"
              name="Blocked"
              stroke="#c74646"
              strokeWidth={2.5}
              dot={{ r: 3 }}
            />

            <Line
              dataKey="review"
              name="Review"
              stroke="#b7791f"
              strokeWidth={2.5}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Top Risk Reasons */}
      <div className="chart-card">
        <h3>Top Risk Reasons</h3>

        <div className="reason-list">
          {reasons.map((item, index) => (
            <div className="reason-row" key={item.reason}>
              <span className="reason-label">{item.reason}</span>

              <div className="reason-track">
                <div
                  className="reason-fill"
                  style={{
                    width: `${
                      (item.count / maxReasonCount) * 100
                    }%`,
                    background:
                      REASON_COLORS[index % REASON_COLORS.length],
                  }}
                />
              </div>

              <span className="reason-pct">
                {reasonsTotal > 0
                  ? `${Math.round(
                      (item.count / reasonsTotal) * 100,
                    )}%`
                  : "0%"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ReportCharts;