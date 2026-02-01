import type { JobProgress } from "../types/wsEvents";

interface StreamProgressProps {
  connected: boolean;
  error?: boolean;
  jobs: Record<string, JobProgress>;
}

export default function StreamProgress({ connected, error, jobs }: StreamProgressProps) {
  const status = error ? "error" : connected ? "live" : "offline";
  const label = status === "error" ? "Server Error" : status === "live" ? "Live" : "Offline";

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-block w-2.5 h-2.5 rounded-full ${
          status === "error"
            ? "theme-status-error"
            : status === "live"
            ? "theme-status-live"
            : "theme-status-offline"
        }`}
      />
      <span className="text-sm font-medium theme-text-inverse status-tag">{label}</span>
    </div>
  );
}
