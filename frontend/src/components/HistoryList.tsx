import type { HistoryItem } from "../api";

interface HistoryListProps {
  title: string;
  history: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
}

export default function HistoryList({ title, history, onSelect }: HistoryListProps) {
  return (
    <aside className="section-card h-full p-3 shadow-sm overflow-auto scrollbar-hidden">
      <h3 className="section-title">{title}</h3>

      {history.length === 0 ? (
        <p className="text-sm theme-text-secondary">
          No feedback yet. Submit something to get started.
        </p>
      ) : (
        <div className="flex flex-col">
          {history.map((h) => (
            <div
              key={h.id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(h)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(h);
                }
              }}
              className="flex items-start gap-3 py-2 px-1 transition cursor-pointer theme-row-hover"
            >
              <span className="text-xs theme-text-tertiary whitespace-nowrap shrink-0 pt-0.5">
                {new Date(h.createdAt).toLocaleString("en-US", {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              <p className="text-sm flex-1 line-clamp-2 theme-text-primary">{h.summary}</p>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
