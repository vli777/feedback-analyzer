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
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selected, setSelected] = useState<InsightRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { connected, jobs, pendingItems, flushPending } = useEventStream();
  const prevCompletedRef = useRef<Set<string>>(new Set());

  const loadAll = useCallback(async () => {
    try {
      setError(null);
      const [hist, mets] = await Promise.all([fetchHistory(), fetchMetrics()]);
      setHistory(hist);
      setMetrics(mets);
      if (!selected && hist.length > 0) {
        setSelected(hist[0]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load data");
    }
  }, [selected]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSubmit = async () => {
    const trimmed = text.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);

    try {
      const record = await sendFeedback(trimmed);
      setSelected(record);
      setText("");
      await loadAll();
    } catch (err) {
      console.error(err);
      setError("Failed to submit feedback");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistory = (item: HistoryItem) => {
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

    // Incrementally update sentiment distribution
    setMetrics((prev) => {
      if (!prev) return prev;
      const dist = { ...prev.sentimentDistribution };
      for (const item of pendingItems) {
        dist[item.sentiment] = (dist[item.sentiment] ?? 0) + 1;
      }
      return { ...prev, sentimentDistribution: dist };
    });

    flushPending();
  }, [pendingItems, flushPending]);

  // On job.completed, do a full reconciliation from server
  useEffect(() => {
    const completedIds = new Set(
      Object.values(jobs)
        .filter((j) => j.completed)
        .map((j) => j.jobId)
    );
    const prev = prevCompletedRef.current;
    let hasNew = false;
    for (const id of completedIds) {
      if (!prev.has(id)) {
        hasNew = true;
        break;
      }
    }
    prevCompletedRef.current = completedIds;
    if (hasNew) {
      loadAll();
    }
  }, [jobs, loadAll]);

  return (
    <main className="dashboard-grid p-6 overflow-hidden">
      {/* Row 1 Col 1 */}
      <div className="grid-sentiment section-card h-full flex flex-col p-4 rounded-xl shadow-sm min-h-0">
        <h3 className="section-title">Sentiment Distribution</h3>
        <div className="flex-1 min-h-0">
          <MetricsPanel metrics={metrics} type="sentiment" />
        </div>
      </div>

      {/* Row 1 Col 2 */}
      <div className="grid-hourly section-card h-full flex flex-col p-4 rounded-xl shadow-sm min-h-0">
        <h3 className="section-title">Submissions by Hour</h3>
        <div className="flex-1 min-h-0">
          <MetricsPanel metrics={metrics} type="hourly" />
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
      <div className="grid-topics section-card h-full flex flex-col p-4 rounded-xl shadow-sm min-h-0">
        <h3 className="section-title">Top Topics</h3>
        <div className="flex-1 min-h-0 overflow-auto">
          <MetricsPanel metrics={metrics} type="topics" />
        </div>
      </div>

      {/* Row 2 Col 2 */}
      <div className="grid-user section-card h-full flex flex-col p-4 rounded-xl shadow-sm min-h-0">
        <h3 className="section-title">User Metrics</h3>
        <div className="flex-1 min-h-0 overflow-auto">
          {selected && <InsightPanel record={selected} />}
        </div>
      </div>

      {/* Row 3 Col 1–2 */}
      <div className="grid-feedback section-card h-full flex flex-col p-4 rounded-xl shadow-sm min-h-0">
        <div className="flex items-start justify-between gap-4 mb-2">
          <div className="flex-1">
            <FeedbackForm
              title="Submit Feedback"
              text={text}
              setText={setText}
              loading={loading}
              error={error}
              onSubmit={handleSubmit}
            />
          </div>
          <div className="w-48 shrink-0">
            <StreamProgress connected={connected} jobs={jobs} />
          </div>
        </div>
      </div>
    </main>
  );
}

export default App;
