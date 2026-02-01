import { useCallback, useEffect, useReducer, useRef } from "react";
import { WS_URL } from "../api";
import type {
  WsEvent,
  ItemAnalyzedPayload,
  JobProgress,
} from "../types/wsEvents";

// ── State ────────────────────────────────────────────────────────────

interface State {
  connected: boolean;
  error: boolean;
  jobs: Record<string, JobProgress>;
  pendingItems: ItemAnalyzedPayload[];
  lastSeqByJob: Record<string, number>;
}

const initialState: State = {
  connected: false,
  error: false,
  jobs: {},
  pendingItems: [],
  lastSeqByJob: {},
};

// ── Actions ──────────────────────────────────────────────────────────

type Action =
  | { type: "CONNECTED" }
  | { type: "DISCONNECTED" }
  | { type: "ERROR" }
  | { type: "EVENT"; event: WsEvent }
  | { type: "FLUSH_PENDING" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "CONNECTED":
      return { ...state, connected: true, error: false };

    case "DISCONNECTED":
      return { ...state, connected: false };

    case "ERROR":
      return { ...state, error: true };

    case "EVENT": {
      const { event } = action;
      const { jobId, seq } = event;

      // Dedup: skip if we've already seen this seq for this job
      if (seq <= (state.lastSeqByJob[jobId] ?? 0)) {
        return state;
      }

      const nextSeqs = { ...state.lastSeqByJob, [jobId]: seq };

      if (event.type === "job.started") {
        const payload = event.payload as { totalItems: number };
        return {
          ...state,
          lastSeqByJob: nextSeqs,
          jobs: {
            ...state.jobs,
            [jobId]: {
              jobId,
              totalItems: payload.totalItems,
              processedItems: 0,
              failedItems: 0,
              completed: false,
            },
          },
        };
      }

      if (event.type === "item.analyzed") {
        const payload = event.payload as ItemAnalyzedPayload;
        const existing = state.jobs[jobId];
        return {
          ...state,
          lastSeqByJob: nextSeqs,
          pendingItems: [...state.pendingItems, payload],
          jobs: existing
            ? {
                ...state.jobs,
                [jobId]: {
                  ...existing,
                  processedItems: existing.processedItems + 1,
                },
              }
            : state.jobs,
        };
      }

      if (event.type === "job.completed") {
        const payload = event.payload as {
          totalItems: number;
          processedItems: number;
          failedItems: number;
        };
        return {
          ...state,
          lastSeqByJob: nextSeqs,
          jobs: {
            ...state.jobs,
            [jobId]: {
              jobId,
              totalItems: payload.totalItems,
              processedItems: payload.processedItems,
              failedItems: payload.failedItems,
              completed: true,
            },
          },
        };
      }

      return { ...state, lastSeqByJob: nextSeqs };
    }

    case "FLUSH_PENDING":
      return { ...state, pendingItems: [] };

    default:
      return state;
  }
}

// ── Hook ─────────────────────────────────────────────────────────────

export function useEventStream() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const delayRef = useRef(1000);
  const mountedRef = useRef(false);
  const closeOnOpenRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;
      if (
        wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING
      )
        return;

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (closeOnOpenRef.current) {
          closeOnOpenRef.current = false;
          ws.close();
          return;
        }
        dispatch({ type: "CONNECTED" });
        delayRef.current = 1000;
      };

      ws.onmessage = (evt) => {
        try {
          const event: WsEvent = JSON.parse(evt.data);
          dispatch({ type: "EVENT", event });
        } catch {
          // Ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        dispatch({ type: "DISCONNECTED" });
        wsRef.current = null;
        if (!mountedRef.current) return;
        reconnectTimer.current = setTimeout(() => {
          delayRef.current = Math.min(delayRef.current * 2, 30000);
          connect();
        }, delayRef.current);
      };

      ws.onerror = () => {
        dispatch({ type: "ERROR" });
        // Let the browser handle the failure; onclose will trigger reconnect.
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current?.readyState === WebSocket.CONNECTING) {
        closeOnOpenRef.current = true;
        return;
      }
      wsRef.current?.close();
    };
  }, []);

  const flushPending = useCallback(() => {
    dispatch({ type: "FLUSH_PENDING" });
  }, []);

  return {
    connected: state.connected,
    error: state.error,
    jobs: state.jobs,
    pendingItems: state.pendingItems,
    flushPending,
  };
}
