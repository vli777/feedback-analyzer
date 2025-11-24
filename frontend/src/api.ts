const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type Sentiment = "positive" | "neutral" | "negative";

export interface FeedbackRecord {
  id: string;
  text: string;
  userId?: string | null;
  sentiment: Sentiment;
  keyTopics: string[];
  actionRequired: boolean;
  summary: string;
  createdAt: string; // ISO
}

export interface HistoryItem {
  id: string;
  userId?: string | null;
  summary: string;
  createdAt: string;
  sentiment: Sentiment;
}

export interface Metrics {
  sentimentDistribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  submissionsByHour: { hour: number; count: number }[];
  topTopics: { topic: string; count: number }[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `API error ${res.status} ${res.statusText}${text ? ` - ${text}` : ""}`
    );
  }

  return res.json() as Promise<T>;
}

export async function sendFeedback(
  text: string,
  userId?: string
): Promise<FeedbackRecord> {
  const data = await request<{ record: FeedbackRecord }>("/feedback", {
    method: "POST",
    body: JSON.stringify({ text, userId }),
  });
  return data.record;
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/history");
}

export async function fetchMetrics(): Promise<Metrics> {
  return request<Metrics>("/metrics");
}
