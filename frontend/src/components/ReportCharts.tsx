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
  HIGH: "#e07856",
  MEDIUM: "#c8963e",
  LOW: "#3f9c6d",
  MINIMAL: "#3d6fb4",
};

const FALLBACK_COLORS = [
  "#c74646",
  "#c8963e",
  "#3f9c6d",
  "#3d6fb4",
  "#7c5cbf",
];

const REASON_COLORS = [
  "#c74646",
  "#d9903f",
  "#c8ab3e",
  "#3f9c6d",
  "#3d6fb4",
  "#7c5cbf",
];

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number | string; color: string }[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="chart-tooltip">
      {label && <div className="chart-tooltip-label">{label}</div>}

      {payload.map((entry, index) => (
        <div className="chart-tooltip-row" key={index}>
          <span
            className="chart-tooltip-dot"
            style={{ background: entry.color }}
          />
          <span className="chart-tooltip-name">{entry.name}</span>
          <strong className="chart-tooltip-value">{entry.value}</strong>
        </div>
      ))}
    </div>
  );
}

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
              <defs>
                {riskData.map((gradientEntry, index) => (
                  <linearGradient
                    id={`donut-gradient-${index}`}
                    key={index}
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor={gradientEntry.color}
                      stopOpacity={0.92}
                    />
                    <stop
                      offset="100%"
                      stopColor={gradientEntry.color}
                      stopOpacity={0.72}
                    />
                  </linearGradient>
                ))}
              </defs>

              <Pie
                data={riskData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={62}
                outerRadius={88}
                paddingAngle={3}
                stroke="var(--surface)"
                strokeWidth={2}
              >
                {riskData.map((_entry, index) => (
                  <Cell
                    key={index}
                    fill={`url(#donut-gradient-${index})`}
                  />
                ))}
              </Pie>

              <Tooltip content={<ChartTooltip />} />
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
              vertical={false}
            />

            <XAxis
              dataKey="date"
              tick={{ fontSize: 11.5, fill: "#8a94a6" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />

            <YAxis
              tick={{ fontSize: 11.5, fill: "#8a94a6" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
              width={36}
            />

            <Tooltip
              content={<ChartTooltip />}
              cursor={{ stroke: "#dfe5ec", strokeWidth: 1 }}
            />

            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 12.5, paddingTop: 8 }}
            />

            <Line
              type="monotone"
              dataKey="allow"
              name="Allowed"
              stroke="#3f9c6d"
              strokeWidth={2.25}
              dot={{ r: 2.5, strokeWidth: 0, fill: "#3f9c6d" }}
              activeDot={{ r: 4.5 }}
            />

            <Line
              type="monotone"
              dataKey="block"
              name="Blocked"
              stroke="#c74646"
              strokeWidth={2.25}
              dot={{ r: 2.5, strokeWidth: 0, fill: "#c74646" }}
              activeDot={{ r: 4.5 }}
            />

            <Line
              type="monotone"
              dataKey="review"
              name="Review"
              stroke="#c8963e"
              strokeWidth={2.25}
              dot={{ r: 2.5, strokeWidth: 0, fill: "#c8963e" }}
              activeDot={{ r: 4.5 }}
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

          {reasons.length === 0 && (
            <p className="chart-empty-note">
              No return-reason data recorded yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ReportCharts;