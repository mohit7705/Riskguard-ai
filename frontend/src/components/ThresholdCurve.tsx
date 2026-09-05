import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceDot,
  ResponsiveContainer,
} from "recharts"
import { SlidersHorizontal } from "lucide-react"
import type { ThresholdCurve as ThresholdCurveData } from "../api/report"

type Props = {
  curve?: ThresholdCurveData
}

function ThresholdTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { name: string; value: number; color: string }[]
  label?: string
}) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">Threshold {label}</div>

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
  )
}

function ThresholdCurve({ curve }: Props) {
  if (!curve || curve.points.length === 0) {
    return null
  }

  const chartData = curve.points.map((point) => ({
    threshold: point.threshold,
    "Precision (%)": Math.round(point.precision * 10000) / 100,
    "Recall (%)": Math.round(point.recall * 10000) / 100,
    "Business Cost": point.business_cost,
  }))

  const pctValues = chartData.flatMap((point) => [
    point["Precision (%)"],
    point["Recall (%)"],
  ])
  const pctFloor = Math.max(
    0,
    Math.floor(Math.min(...pctValues) / 5) * 5 - 5,
  )

  const selectedPoint = chartData.find(
    (point) => point.threshold === curve.selected_threshold,
  )

  return (
    <div className="chart-card threshold-curve-card">
      <div className="threshold-curve-header">
        <div>
          <h3>Threshold vs. Cost Tradeoff</h3>

          <span className="model-perf-meta">
            Selected threshold {curve.selected_threshold} · FP
            cost {curve.false_positive_cost} · FN cost{" "}
            {curve.false_negative_cost}
          </span>
        </div>

        <div className="threshold-curve-icon">
          <SlidersHorizontal size={18} strokeWidth={2.2} />
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={chartData}
          margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#eef1f5"
            vertical={false}
          />

          <XAxis
            dataKey="threshold"
            tick={{ fontSize: 11.5, fill: "#8a94a6" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
            label={{
              value: "Decision Threshold",
              position: "insideBottom",
              offset: -4,
              fontSize: 11.5,
              fill: "#8a94a6",
            }}
          />

          <YAxis
            yAxisId="pct"
            domain={[pctFloor, 100]}
            tick={{ fontSize: 11.5, fill: "#8a94a6" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
            width={38}
            label={{
              value: "%",
              angle: -90,
              position: "insideLeft",
              fontSize: 11.5,
              fill: "#8a94a6",
            }}
          />

          <YAxis
            yAxisId="cost"
            orientation="right"
            tick={{ fontSize: 11.5, fill: "#8a94a6" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
            width={40}
            label={{
              value: "Business Cost",
              angle: 90,
              position: "insideRight",
              fontSize: 11.5,
              fill: "#8a94a6",
            }}
          />

          <Tooltip content={<ThresholdTooltip />} />

          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 12.5, paddingTop: 10 }}
          />

          <ReferenceLine
            x={curve.selected_threshold}
            yAxisId="pct"
            stroke="var(--navy)"
            strokeDasharray="4 4"
            label={{
              value: "Selected",
              position: "top",
              fontSize: 11,
              fill: "#18263d",
              fontWeight: 700,
            }}
          />

          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="Precision (%)"
            stroke="#3d6fb4"
            strokeWidth={2.25}
            dot={false}
            activeDot={{ r: 4.5 }}
          />

          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="Recall (%)"
            stroke="#3f9c6d"
            strokeWidth={2.25}
            dot={false}
            activeDot={{ r: 4.5 }}
          />

          <Line
            yAxisId="cost"
            type="monotone"
            dataKey="Business Cost"
            stroke="#c74646"
            strokeWidth={1.75}
            strokeDasharray="5 3"
            dot={false}
            activeDot={{ r: 4.5 }}
          />

          {selectedPoint && (
            <ReferenceDot
              yAxisId="pct"
              x={selectedPoint.threshold}
              y={selectedPoint["Precision (%)"]}
              r={5}
              fill="var(--navy)"
              stroke="#ffffff"
              strokeWidth={2}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      <p className="threshold-curve-note">
        {curve.selection_reason}
      </p>
    </div>
  )
}

export default ThresholdCurve