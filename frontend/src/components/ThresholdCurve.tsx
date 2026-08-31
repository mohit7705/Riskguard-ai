import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts"
import { SlidersHorizontal } from "lucide-react"
import type { ThresholdCurve as ThresholdCurveData } from "../api/report"

type Props = {
  curve?: ThresholdCurveData
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
          />

          <XAxis
            dataKey="threshold"
            tick={{ fontSize: 12, fill: "#7b8798" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
            label={{
              value: "Decision Threshold",
              position: "insideBottom",
              offset: -2,
              fontSize: 12,
              fill: "#7b8798",
            }}
          />

          <YAxis
            yAxisId="pct"
            domain={[0, 100]}
            tick={{ fontSize: 12, fill: "#7b8798" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
            label={{
              value: "%",
              angle: -90,
              position: "insideLeft",
              fontSize: 12,
              fill: "#7b8798",
            }}
          />

          <YAxis
            yAxisId="cost"
            orientation="right"
            tick={{ fontSize: 12, fill: "#7b8798" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
            label={{
              value: "Business Cost",
              angle: 90,
              position: "insideRight",
              fontSize: 12,
              fill: "#7b8798",
            }}
          />

          <Tooltip />

          <Legend
            iconType="circle"
            wrapperStyle={{ fontSize: 13 }}
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
            dataKey="Precision (%)"
            stroke="#2b5fb0"
            strokeWidth={2.5}
            dot={{ r: 3 }}
          />

          <Line
            yAxisId="pct"
            dataKey="Recall (%)"
            stroke="#198754"
            strokeWidth={2.5}
            dot={{ r: 3 }}
          />

          <Line
            yAxisId="cost"
            dataKey="Business Cost"
            stroke="#c74646"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="threshold-curve-note">
        {curve.selection_reason}
      </p>
    </div>
  )
}

export default ThresholdCurve
