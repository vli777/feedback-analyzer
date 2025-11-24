import type { HistoryItem } from "../api";

interface HistoryListProps {
  title: string;
  history: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
}

export default function HistoryList({ title, history, onSelect }: HistoryListProps) {
  return (
    <aside className="section-card h-full p-4 rounded-xl shadow-sm overflow-auto">
      <h3 className="section-title">{title}</h3>

      {history.length === 0 ? (
        <p className="text-sm text-slate-500">
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
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelect(h);
                }
              }}
              className="flex items-start gap-3 py-2 px-1 hover:bg-slate-50 transition cursor-pointer border-b border-slate-200 last:border-b-0"
            >
              <span className="text-xs text-slate-500 whitespace-nowrap shrink-0 pt-0.5">
                {new Date(h.createdAt).toLocaleString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
              <p className="text-sm flex-1 line-clamp-2">{h.summary}</p>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
