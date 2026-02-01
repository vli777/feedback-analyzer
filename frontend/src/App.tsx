import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import {
  sendFeedback,
  fetchHistory,
  fetchMetrics,
  type HistoryItem,
  type Metrics,
} from "./api";
import { useEventStream } from "./hooks/useEventStream";
import MetricsPanel from "./components/MetricsPanel";
import FeedbackForm from "./components/FeedbackForm";
import HistoryList from "./components/HistoryList";
import StreamProgress from "./components/StreamProgress";
import "./App.css";

type SparklineProps = {
  points: number[];
};

function Sparkline({ points }: SparklineProps) {
  const safePoints = points.length > 1 ? points : [0, 0];
  const min = Math.min(...safePoints);
  const max = Math.max(...safePoints);
  const range = max - min || 1;
  const coords = safePoints.map((value, idx) => {
    const x = (idx / (safePoints.length - 1)) * 100;
    const y = 100 - ((value - min) / range) * 100;
    return `${x},${y}`;
  });

  return (
    <svg className="sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline points={coords.join(" ")} fill="none" />
    </svg>
  );
}

function App() {
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { connected, error: streamError, jobs, pendingItems, flushPending } = useEventStream();
  const prevCompletedRef = useRef<Set<string>>(new Set());
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const BUCKET_MINUTES = 5;
  const WINDOW_MINUTES = 60;
  const BUCKET_COUNT = WINDOW_MINUTES / BUCKET_MINUTES;

  const floorToBucket = (date: Date) => {
    const floored = new Date(date);
    floored.setUTCSeconds(0, 0);
    floored.setUTCMinutes(floored.getUTCMinutes() - (floored.getUTCMinutes() % BUCKET_MINUTES));
    return floored;
  };

  const formatBucket = (date: Date) =>
    `${date.getUTCHours().toString().padStart(2, "0")}:${date
      .getUTCMinutes()
      .toString()
      .padStart(2, "0")}`;

  const loadAll = useCallback(async () => {
    try {
      setError(null);
      const [hist, mets] = await Promise.all([fetchHistory(), fetchMetrics()]);
      setHistory(hist);
      setMetrics((prev) => {
        if (!prev) return mets;
        return {
          ...mets,
          submissionsByTime:
            prev.submissionsByTime.length > 0
              ? prev.submissionsByTime
              : mets.submissionsByTime,
        };
      });
    } catch (err) {
      console.error(err);
      setError("Failed to load data");
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const visibilityMetrics = useMemo(() => {
    if (!metrics) {
      return null;
    }

    const timeBuckets = metrics.submissionsByTime;
    const totals = timeBuckets.map((b) => b.count);
    const lastTotal = totals[totals.length - 1] ?? 0;
    const prevTotal = totals[totals.length - 2] ?? 0;
    const throughputDelta = lastTotal - prevTotal;

    const sentimentTotals = timeBuckets.map((b) => b.positive + b.neutral + b.negative);
    const sentimentNet = timeBuckets.map((b, idx) => {
      const total = sentimentTotals[idx] || 1;
      return (b.positive - b.negative) / total;
    });
    const lastSentimentNet = sentimentNet[sentimentNet.length - 1] ?? 0;

    const topicTrends = metrics.topicTrends ?? [];
    let topTopic = "—";
    let topTopicDelta = 0;
    let topTopicSeries: number[] = [];
    if (topicTrends.length > 0) {
      const last = topicTrends[topicTrends.length - 1];
      const prev = topicTrends[topicTrends.length - 2];
      const topicNames = Object.keys(last).filter((k) => k !== "date");
      let bestDelta = -Infinity;
      for (const name of topicNames) {
        const lastVal = typeof last[name] === "number" ? (last[name] as number) : 0;
        const prevVal = prev && typeof prev[name] === "number" ? (prev[name] as number) : 0;
        const delta = lastVal - prevVal;
        if (delta > bestDelta) {
          bestDelta = delta;
          topTopic = name;
          topTopicDelta = delta;
        }
      }
      if (topTopic !== "—") {
        topTopicSeries = topicTrends.map((p) =>
          typeof p[topTopic] === "number" ? (p[topTopic] as number) : 0
        );
      }
    }

    const negShare = timeBuckets.map((b, idx) => {
      const total = sentimentTotals[idx] || 1;
      return b.negative / total;
    });
    const lastNeg = negShare[negShare.length - 1] ?? 0;
    const prevNeg = negShare[negShare.length - 2] ?? 0;
    const alertDelta = lastNeg - prevNeg;
    const alertLevel = alertDelta > 0.2 ? "surge" : alertDelta > 0.1 ? "watch" : "normal";

    return {
      totals,
      throughput: {
        value: lastTotal,
        delta: throughputDelta,
      },
      sentiment: {
        series: sentimentNet,
        value: lastSentimentNet,
      },
      topics: {
        name: topTopic,
        delta: topTopicDelta,
        series: topTopicSeries,
      },
      alert: {
        level: alertLevel,
        delta: alertDelta,
      },
    };
  }, [metrics]);

  const handleSubmit = async (rawText: string) => {
    const trimmed = rawText.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);

    try {
      await sendFeedback(trimmed);
      await loadAll();
      return true;
    } catch (err) {
      console.error(err);
      setError("Failed to submit feedback");
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Incrementally add WS-streamed items to history and metrics
  useEffect(() => {
    if (pendingItems.length === 0) return;

    const newHistoryItems: HistoryItem[] = pendingItems.map((item) => ({
      id: crypto.randomUUID(),
      userId: null,
      summary: item.summary,
      createdAt: new Date().toISOString(),
      sentiment: item.sentiment,
    }));

    setHistory((prev) => [...newHistoryItems.reverse(), ...prev]);
    // Incrementally update sentiment + buckets + top topics
    setMetrics((prev) => {
      if (!prev) return prev;
      const dist = { ...prev.sentimentDistribution };
      const topicMap = new Map(prev.topTopics.map((t) => [t.topic, t.count]));
      const now = new Date();
      const windowEnd = floorToBucket(now);
      const windowStart = new Date(
        windowEnd.getTime() - (BUCKET_COUNT - 1) * BUCKET_MINUTES * 60 * 1000
      );
      const bucketLabels: string[] =
        prev.submissionsByTime.length > 0
          ? prev.submissionsByTime.map((b) => b.bucket)
          : Array.from({ length: BUCKET_COUNT }, (_, i) =>
              formatBucket(
                new Date(
                  windowStart.getTime() + i * BUCKET_MINUTES * 60 * 1000
                )
              )
            );
      const bucketMap = new Map(
        prev.submissionsByTime.map((b) => [
          b.bucket,
          {
            count: b.count,
            positive: b.positive,
            neutral: b.neutral,
            negative: b.negative,
          },
        ])
      );
      const updatedBuckets = bucketLabels.map((label) => {
        const current = bucketMap.get(label);
        return {
          bucket: label,
          count: current?.count ?? 0,
          positive: current?.positive ?? 0,
          neutral: current?.neutral ?? 0,
          negative: current?.negative ?? 0,
        };
      });
      const currentBucket = formatBucket(now);
      const currentIdx = updatedBuckets.findIndex((b) => b.bucket === currentBucket);
      if (currentIdx >= 0) {
        const base = updatedBuckets[currentIdx];
        let pos = 0;
        let neu = 0;
        let neg = 0;
        for (const item of pendingItems) {
          if (item.sentiment === "positive") pos += 1;
          else if (item.sentiment === "negative") neg += 1;
          else neu += 1;
        }
        updatedBuckets[currentIdx] = {
          ...base,
          count: base.count + pendingItems.length,
          positive: base.positive + pos,
          neutral: base.neutral + neu,
          negative: base.negative + neg,
        };
      }

      for (const item of pendingItems) {
        dist[item.sentiment] = (dist[item.sentiment] ?? 0) + 1;
        for (const topic of item.keyTopics ?? []) {
          topicMap.set(topic, (topicMap.get(topic) ?? 0) + 1);
        }
      }
      const topTopics = Array.from(topicMap.entries())
        .map(([topic, count]) => ({ topic, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10);

      return {
        ...prev,
        sentimentDistribution: dist,
        submissionsByTime: updatedBuckets,
        topTopics,
      };
    });

    flushPending();
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    refreshTimerRef.current = setTimeout(() => {
      loadAll();
    }, 1000);
  }, [pendingItems, flushPending, loadAll]);

  // Preserve server-backed data without wiping live-only updates.
  useEffect(() => {
    prevCompletedRef.current = new Set(
      Object.values(jobs).filter((j) => j.completed).map((j) => j.jobId)
    );
  }, [jobs]);

  return (
    <div className="dashboard-shell">
      <div className="dashboard-frame">
        <header className="dashboard-header">
          <div className="header-left">
            <img className="logo-mark" src="/vite.svg" alt="Company logo" />
            <div>
              <h1 className="header-title">Feedback Analyzer</h1>
            </div>
          </div>
          <StreamProgress connected={connected} error={streamError} jobs={jobs} />
        </header>
        <main className="dashboard-grid p-4 overflow-hidden">
      {/* Row 1 Col 1 */}
      <div className="grid-sentiment section-card h-full flex flex-col p-3 shadow-sm min-h-0">
        <h3 className="section-title">Sentiment Distribution</h3>
        <div className="flex-1 min-h-0">
          <MetricsPanel metrics={metrics} type="sentiment" />
        </div>
      </div>

      {/* Row 1 Col 2 */}
      <div className="grid-hourly section-card h-full flex flex-col p-3 shadow-sm min-h-0">
        <h3 className="section-title">Submissions Over Time</h3>
        <div className="flex-1 min-h-0">
          <MetricsPanel metrics={metrics} type="time" />
        </div>
      </div>

      {/* Right column spanning all rows */}
      <div className="grid-history h-full flex flex-col min-h-0">
        <HistoryList
          title="Submission History"
          history={history}
        />
      </div>

      {/* Row 2 Col 1 */}
      <div className="grid-topics section-card h-full flex flex-col p-3 shadow-sm min-h-0">
        <h3 className="section-title">Top Topics</h3>
        <div className="flex-1 min-h-0 overflow-auto">
          <MetricsPanel metrics={metrics} type="topics" />
        </div>
      </div>

      {/* Row 2 Col 2 */}
      <div className="grid-user section-card h-full flex flex-col p-3 shadow-sm min-h-0">
        <h3 className="section-title">Visibility Metrics</h3>
        <div className="flex-1 min-h-0 overflow-auto">
          <div className="visibility-grid">
            <div className="visibility-card">
              <p className="visibility-label ui-tag">Throughput</p>
              <div className="visibility-row">
                <span className="visibility-value">{visibilityMetrics?.throughput.value ?? 0}</span>
                <span className="visibility-delta">
                  {visibilityMetrics?.throughput.delta ?? 0}
                </span>
              </div>
              <Sparkline points={visibilityMetrics?.totals ?? []} />
            </div>
            <div className="visibility-card">
              <p className="visibility-label ui-tag">Sentiment Mix</p>
              <div className="visibility-row">
                <span className="visibility-value">
                  {Math.round(((visibilityMetrics?.sentiment.value ?? 0) + 1) * 50)}%
                </span>
                <span className="visibility-delta">Net</span>
              </div>
              <Sparkline points={visibilityMetrics?.sentiment.series ?? []} />
            </div>
            <div className="visibility-card">
              <p className="visibility-label ui-tag">Top Topic Velocity</p>
              <div className="visibility-row">
                <span className="visibility-value">{visibilityMetrics?.topics.name ?? "—"}</span>
                <span className="visibility-delta">
                  {visibilityMetrics?.topics.delta ?? 0}
                </span>
              </div>
              <Sparkline points={visibilityMetrics?.topics.series ?? []} />
            </div>
            <div className="visibility-card">
              <p className="visibility-label ui-tag">Alerting</p>
              <div className="visibility-row">
                <span className="visibility-value">
                  {visibilityMetrics?.alert.level ?? "normal"}
                </span>
                <span className="visibility-delta">
                  {Math.round((visibilityMetrics?.alert.delta ?? 0) * 100)}%
                </span>
              </div>
              <Sparkline points={(visibilityMetrics?.alert.level ? visibilityMetrics?.totals : []) ?? []} />
            </div>
          </div>
        </div>
      </div>

      {/* Row 3 Col 1–2 */}
      <div className="grid-feedback section-card h-full flex flex-col p-3 shadow-sm min-h-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="section-title mb-0">Submit Feedback</h3>
        </div>
        <FeedbackForm
          title=""
          loading={loading}
          error={error}
          onSubmit={handleSubmit}
        />
      </div>
        </main>
      </div>
    </div>
  );
}

export default App;
