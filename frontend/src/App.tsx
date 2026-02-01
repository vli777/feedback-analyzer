import { useEffect, useState, useCallback, useRef } from "react";
import {
  sendFeedback,
  fetchHistory,
  fetchMetrics,
  type FeedbackRecord,
  type HistoryItem,
  type Metrics,
} from "./api";
import { useEventStream } from "./hooks/useEventStream";
import InsightPanel from "./components/InsightPanel";
import MetricsPanel from "./components/MetricsPanel";
import FeedbackForm from "./components/FeedbackForm";
import HistoryList from "./components/HistoryList";
import StreamProgress from "./components/StreamProgress";
import "./App.css";

type InsightRecord = FeedbackRecord | HistoryItem;

function App() {
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selected, setSelected] = useState<InsightRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { connected, error: streamError, jobs, pendingItems, flushPending } = useEventStream();
  const prevCompletedRef = useRef<Set<string>>(new Set());
  const userSelectedRef = useRef(false);
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
      if (!userSelectedRef.current && hist.length > 0) {
        setSelected(hist[0]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load data");
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSubmit = async (rawText: string) => {
    const trimmed = rawText.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    userSelectedRef.current = false;

    try {
      const record = await sendFeedback(trimmed);
      setSelected(record);
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

  const handleSelectHistory = (item: HistoryItem) => {
    userSelectedRef.current = true;
    setSelected(item);
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
    if (!userSelectedRef.current && newHistoryItems.length > 0) {
      setSelected(newHistoryItems[0]);
    }

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
      const bucketMap = new Map(prev.submissionsByTime.map((b) => [b.bucket, b.count]));
      const updatedBuckets = bucketLabels.map((label) => ({
        bucket: label,
        count: bucketMap.get(label) ?? 0,
      }));
      const currentBucket = formatBucket(now);
      const currentIdx = updatedBuckets.findIndex((b) => b.bucket === currentBucket);
      if (currentIdx >= 0) {
        updatedBuckets[currentIdx] = {
          ...updatedBuckets[currentIdx],
          count: updatedBuckets[currentIdx].count + pendingItems.length,
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
              <h1 className="header-title">Dashboard Title</h1>
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
          onSelect={handleSelectHistory}
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
        <h3 className="section-title">User Metrics</h3>
        <div className="flex-1 min-h-0 overflow-auto">
          {selected && <InsightPanel record={selected} />}
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
