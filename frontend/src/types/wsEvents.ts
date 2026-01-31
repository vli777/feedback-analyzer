import type { Sentiment } from "../api";

export interface WsEvent {
  jobId: string;
  seq: number;
  type: "job.started" | "item.analyzed" | "job.completed";
  ts: string; // ISO-8601
  payload: JobStartedPayload | ItemAnalyzedPayload | JobCompletedPayload;
}

export interface JobStartedPayload {
  totalItems: number;
}

export interface ItemAnalyzedPayload {
  index: number;
  text: string;
  sentiment: Sentiment;
  keyTopics: string[];
  actionRequired: boolean;
  summary: string;
}

export interface JobCompletedPayload {
  totalItems: number;
  processedItems: number;
  failedItems: number;
}

export interface JobProgress {
  jobId: string;
  totalItems: number;
  processedItems: number;
  failedItems: number;
  completed: boolean;
}
