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
        <div className="space-y-2">
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
              className="w-full text-left border rounded-md px-2 py-2 bg-white hover:bg-slate-50 transition cursor-pointer"
            >
              <p className="text-sm font-medium line-clamp-2">{h.summary}</p>
              <p className="text-xs text-slate-500 mt-1">
                {h.sentiment} · {new Date(h.createdAt).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
