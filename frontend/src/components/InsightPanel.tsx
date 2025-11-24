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
  const sortedTopics = isFull ? [...record.keyTopics].sort() : [];

  return (
    <div className="text-sm space-y-4">
      {/* Original Submission */}
      {isFull && "text" in record && (
        <div>
          <p className="font-semibold text-slate-700 mb-1">Original Submission:</p>
          <p className="text-slate-600 p-3 bg-slate-50 rounded-lg border border-slate-200">
            {record.text}
          </p>
        </div>
      )}

      {/* Summary */}
      {"summary" in record && (
        <div>
          <p className="font-semibold text-slate-700 mb-1">Summary:</p>
          <p className="text-slate-600">{record.summary}</p>
        </div>
      )}

      {/* Sentiment */}
      <div>
        <p className="font-semibold text-slate-700 mb-1">Sentiment:</p>
        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
          record.sentiment === "positive" ? "bg-green-100 text-green-700" :
          record.sentiment === "negative" ? "bg-red-100 text-red-700" :
          "bg-slate-100 text-slate-700"
        }`}>
          {record.sentiment.charAt(0).toUpperCase() + record.sentiment.slice(1)}
        </span>
      </div>

      {/* Topics */}
      {isFull && (
        <div>
          <p className="font-semibold text-slate-700 mb-2">Topics:</p>
          {sortedTopics.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {sortedTopics.map((topic) => (
                <span
                  key={topic}
                  className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-sm"
                >
                  {topic}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-slate-500">No topics</p>
          )}
        </div>
      )}

      {/* Action Required */}
      {isFull && (
        <div>
          <p className="font-semibold text-slate-700 mb-1">Action Required:</p>
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
            record.actionRequired ? "bg-orange-100 text-orange-700" : "bg-slate-100 text-slate-700"
          }`}>
            {record.actionRequired ? "Yes" : "No"}
          </span>
        </div>
      )}

      {/* Submission Time */}
      <div>
        <p className="font-semibold text-slate-700 mb-1">Submitted:</p>
        <p className="text-slate-600">
          {new Date(record.createdAt).toLocaleString("en-US", {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
      </div>
    </div>
  );
}
