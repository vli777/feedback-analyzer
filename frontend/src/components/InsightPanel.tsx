import type { FeedbackRecord, HistoryItem } from "../api";

type InsightRecord = FeedbackRecord | HistoryItem;

interface InsightPanelProps {
  record: InsightRecord | null;
}

export default function InsightPanel({ record }: InsightPanelProps) {
  if (!record) {
    return (
      <div className="text-sm text-slate-500">
        Select a feedback item from history.
      </div>
    );
  }

  const isFull = "keyTopics" in record && "actionRequired" in record;

  return (
    <div className="text-sm space-y-2">
      <p className="text-slate-600">
        <span className="font-semibold">Sentiment:</span>{" "}
        <span className="font-medium">{record.sentiment}</span>
      </p>

      {"summary" in record && (
        <p>
          <span className="font-semibold">Summary:</span> {record.summary}
        </p>
      )}

      {isFull && (
        <>
          <p>
            <span className="font-semibold">Topics:</span>{" "}
            {record.keyTopics.length ? record.keyTopics.join(", ") : "—"}
          </p>
          <p>
            <span className="font-semibold">Action Required:</span>{" "}
            {record.actionRequired ? "Yes" : "No"}
          </p>
        </>
      )}

      <p className="text-xs text-slate-500">
        {new Date(record.createdAt).toLocaleString()}
      </p>
    </div>
  );
}
