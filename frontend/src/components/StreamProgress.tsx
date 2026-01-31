import type { JobProgress } from "../types/wsEvents";

interface StreamProgressProps {
  connected: boolean;
  jobs: Record<string, JobProgress>;
}

export default function StreamProgress({ connected, jobs }: StreamProgressProps) {
  const activeJobs = Object.values(jobs).filter((j) => !j.completed);
  const recentCompleted = Object.values(jobs)
    .filter((j) => j.completed)
    .slice(-3);

  return (
    <div className="space-y-3">
      {/* Connection indicator */}
      <div className="flex items-center gap-2">
        <span
          className={`inline-block w-2.5 h-2.5 rounded-full ${
            connected ? "bg-green-500" : "bg-red-500"
          }`}
        />
        <span className="text-sm font-medium text-slate-600">
          {connected ? "Live" : "Disconnected"}
        </span>
      </div>

      {/* Active jobs */}
      {activeJobs.map((job) => {
        const pct =
          job.totalItems > 0
            ? Math.round((job.processedItems / job.totalItems) * 100)
            : 0;
        return (
          <div key={job.jobId} className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Processing...</span>
              <span>
                {job.processedItems}/{job.totalItems}
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}

      {/* Recently completed */}
      {recentCompleted.map((job) => (
        <div key={job.jobId} className="text-xs text-slate-500">
          Completed: {job.processedItems} items
          {job.failedItems > 0 && (
            <span className="text-red-500 ml-1">
              ({job.failedItems} failed)
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
