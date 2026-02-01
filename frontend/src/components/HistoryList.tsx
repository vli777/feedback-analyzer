import type { HistoryItem } from "../api";

interface HistoryListProps {
  title: string;
  history: HistoryItem[];
}

export default function HistoryList({ title, history }: HistoryListProps) {
  return (
    <aside className="section-card sidebar-panel h-full p-4 shadow-sm overflow-auto scrollbar-hidden">
      <h3 className="section-title sidebar-title">{title}</h3>

      {history.length === 0 ? (
        <p className="text-sm theme-text-secondary">
          No feedback yet. Submit something to get started.
        </p>
      ) : (
        <div className="flex flex-col">
          {history.map((h) => (
            <div
              key={h.id}
              className="flex items-start gap-3 py-2 px-2 theme-row-hover"
            >
              <span className="text-[10px] theme-text-tertiary whitespace-nowrap shrink-0 pt-0.5">
                {new Date(h.createdAt).toLocaleString("en-US", {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-[9px] ui-tag self-start ${
                      h.sentiment === "positive"
                        ? "theme-badge-positive"
                        : h.sentiment === "negative"
                        ? "theme-badge-negative"
                        : "theme-badge-neutral"
                    }`}
                  >
                    {h.sentiment}
                  </span>
                  <p className="text-xs flex-1 line-clamp-2 theme-text-primary">
                    {h.summary}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
