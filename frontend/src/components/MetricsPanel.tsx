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
  type: "sentiment" | "hourly" | "topics";
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

    return (
      <div className="h-full w-full flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%" maxHeight={300}>
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
            >
              {sentimentData.map((entry, index) => (
                <Cell key={entry.name} fill={SENTIMENT_COLORS[index]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend verticalAlign="bottom" height={36} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "hourly") {
    const hourData = metrics.submissionsByHour.map((h) => ({
      hour: `${h.hour}:00`,
      Submissions: h.count,
    }));

    return (
      <div className="h-full w-full flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%" maxHeight={300}>
          <BarChart data={hourData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
            <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="Submissions" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "topics") {
    const sortedTopics = [...metrics.topTopics].sort((a, b) => b.count - a.count || a.topic.localeCompare(b.topic));

    return (
      <div>
        {sortedTopics.length === 0 ? (
          <p className="text-sm text-slate-500">No topics yet.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-sm">
            {sortedTopics.map((t) => (
              <li
                key={t.topic}
                className="px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200"
              >
                {t.topic} <span className="font-semibold">({t.count})</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return null;
}
