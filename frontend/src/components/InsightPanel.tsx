import type { FeedbackRecord, HistoryItem } from "../api";

type InsightRecord = FeedbackRecord | HistoryItem;

interface InsightPanelProps {
  record: InsightRecord | null;
}

export default function InsightPanel({ record }: InsightPanelProps) {
  if (!record) {
    return (
      <div className="text-sm theme-text-secondary">
        Select a feedback item from history.
      </div>
    );
  }

  const isFull = "keyTopics" in record && "actionRequired" in record;
  const sortedTopics = isFull ? [...record.keyTopics].sort() : [];

  return (
    <div className="text-sm space-y-4 theme-text-secondary">
      {/* Submission Time */}
      <div>
        <p className="font-semibold theme-text-primary mb-1">Submitted:</p>
        <p>
          {new Date(record.createdAt).toLocaleString("en-US", {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
      </div>

      {/* Summary */}
      {"summary" in record && (
        <div>
          <p className="font-semibold theme-text-primary mb-1">Summary:</p>
          <p>{record.summary}</p>
        </div>
      )}

      {/* Sentiment */}
      <div>
        <p className="font-semibold theme-text-primary mb-1">Sentiment:</p>
        <span
          className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
            record.sentiment === "positive"
              ? "theme-badge-positive"
              : record.sentiment === "negative"
              ? "theme-badge-negative"
              : "theme-badge-neutral"
          }`}
        >
          {record.sentiment.charAt(0).toUpperCase() + record.sentiment.slice(1)}
        </span>
      </div>

      {/* Topics */}
      {isFull && (
        <div>
          <p className="font-semibold theme-text-primary mb-2">Topics:</p>
          {sortedTopics.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {sortedTopics.map((topic) => (
                <span
                  key={topic}
                  className="px-3 py-1 rounded-full text-sm theme-chip"
                >
                  {topic}
                </span>
              ))}
            </div>
          ) : (
            <p className="theme-text-tertiary">No topics</p>
          )}
        </div>
      )}

      {/* Action Required */}
      {isFull && (
        <div>
          <p className="font-semibold theme-text-primary mb-1">Action Required:</p>
          <span
            className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              record.actionRequired ? "theme-badge-accent" : "theme-badge-neutral"
            }`}
          >
            {record.actionRequired ? "Yes" : "No"}
          </span>
        </div>
      )}

      {/* Original Submission */}
      {isFull && "text" in record && (
        <div>
          <p className="font-semibold theme-text-primary mb-1">
            Original Submission:
          </p>
          <p className="p-3 shadow-sm theme-bg-secondary">
            {record.text}
          </p>
        </div>
      )}
    </div>
  );
}
