import type { JobProgress } from "../types/wsEvents";

interface StreamProgressProps {
  connected: boolean;
  jobs: Record<string, JobProgress>;
}

export default function StreamProgress({ connected, jobs }: StreamProgressProps) {
  return (
    <div className="flex items-center gap-2">
        <span
          className={`inline-block w-2.5 h-2.5 rounded-full ${
            connected ? "bg-green-500" : "bg-red-500"
          }`}
        />
      <span className="text-sm font-medium text-slate-600">
        {connected ? "Live" : "Offline"}
      </span>
    </div>
  );
}
