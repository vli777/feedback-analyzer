import { useEffect, useMemo, useRef, useState } from "react";
import type { Metrics } from "../api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

interface MetricsPanelProps {
  metrics: Metrics | null;
  type: "sentiment" | "time" | "topics";
}

const SENTIMENT_COLORS = ["#22c55e", "#64748b", "#ef4444"];

export default function MetricsPanel({ metrics, type }: MetricsPanelProps) {
  if (!metrics) {
    return (
      <div className="text-sm text-slate-500">
        Metrics will appear after you submit some feedback.
      </div>
    );
  }

  if (type === "sentiment") {
    const sentimentData = [
      {
        name: "Positive",
        value: metrics.sentimentDistribution.positive,
      },
      {
        name: "Neutral",
        value: metrics.sentimentDistribution.neutral,
      },
      {
        name: "Negative",
        value: metrics.sentimentDistribution.negative,
      },
    ];

    const total = sentimentData.reduce((acc, item) => acc + item.value, 0);
    const percentLabel = (value: number) =>
      total > 0 ? `${Math.round((value / total) * 100)}%` : "0%";

    return (
      <div className="w-full min-w-0 min-h-[260px] flex items-center justify-center">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={sentimentData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="45%"
              innerRadius="40%"
              outerRadius="70%"
              paddingAngle={2}
              label={({ value }) => percentLabel(value as number)}
              labelLine={false}
              isAnimationActive={false}
            >
              {sentimentData.map((entry, index) => (
                <Cell key={entry.name} fill={SENTIMENT_COLORS[index]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [value, "Count"]}
              labelFormatter={(label) => label}
            />
            <Legend verticalAlign="bottom" height={36} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "time") {
    const [scaleBump, setScaleBump] = useState(false);
    const maxDomainRef = useRef(0);

    const hourData = useMemo(
      () =>
        metrics.submissionsByTime.map((h) => ({
          bucket: h.bucket,
          Submissions: h.count,
        })),
      [metrics.submissionsByTime]
    );

    const maxCount = hourData.reduce((acc, item) => Math.max(acc, item.Submissions), 0);
    const paddedMax = Math.max(5, Math.ceil(maxCount * 1.2));

    useEffect(() => {
      if (paddedMax > maxDomainRef.current) {
        maxDomainRef.current = paddedMax;
        setScaleBump(true);
        const timer = setTimeout(() => setScaleBump(false), 600);
        return () => clearTimeout(timer);
      }
      return undefined;
    }, [paddedMax]);

    return (
      <div className="w-full min-w-0 min-h-[260px] flex items-center justify-center">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={hourData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
            <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
            <YAxis
              allowDecimals={false}
              domain={[0, maxDomainRef.current || paddedMax]}
              tick={{
                fontSize: 11,
                fontWeight: scaleBump ? 700 : 400,
              }}
            />
            <Tooltip />
            <Legend />
            <Bar dataKey="Submissions" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "topics") {
    const sortedTopics = [...metrics.topTopics].sort((a, b) => b.count - a.count);

    if (sortedTopics.length === 0) {
      return (
        <div className="text-sm text-slate-500">
          Topic trends will appear after you submit some feedback.
        </div>
      );
    }

    return (
      <div className="w-full min-w-0 min-h-[260px] flex items-center justify-center">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={sortedTopics}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
          >
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="topic"
              tick={{ fontSize: 11 }}
              width={100}
            />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
}
