"use client";

import { useEffect, useState } from "react";
import { Spinner } from "flowbite-react";

type ProgressData = {
  percent: number;
  running: boolean;
  status?: string;
};

type Props = {
  onProgress?: (data: ProgressData) => void;
  onCancel?: () => void;
};

export function ProgressModal({ onProgress, onCancel }: Props) {
  const [data, setData] = useState<ProgressData>({
    percent: 0,
    running: true,
    status: "Initializing...",
  });
  const [cancelling, setCancelling] = useState(false);
  const [mode, setMode] = useState<"ws" | "polling">("ws");

  useEffect(() => {
    if (mode !== "ws") return;

    let ws: WebSocket | null = null;
    let isNewScan = true;

    const connect = () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const wsUrl = `${apiUrl.replace(/^http/, "ws")}/ws/progress`;

      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const nextData: ProgressData = JSON.parse(event.data);

          if (isNewScan && !nextData.running && nextData.percent > 0) {
            return;
          }

          isNewScan = false;
          setData(nextData);
          onProgress?.(nextData);
        } catch { }
      };

      ws.onerror = () => setMode("polling");
      ws.onclose = (event) => {
        if (event.code !== 1000 && event.code !== 1005) {
          setMode("polling");
        }
      };
    };

    connect();
    return () => {
      if (!ws) return;
      ws.onclose = null;
      ws.onerror = null;
      ws.close();
    };
  }, [mode, onProgress]);

  useEffect(() => {
    if (mode !== "polling") return;

    let isNewScan = true;

    const poll = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/progress`);
        if (!res.ok) return;

        const nextData: ProgressData = await res.json();
        if (isNewScan && !nextData.running && nextData.percent > 0) {
          return;
        }

        isNewScan = false;
        setData(nextData);
        onProgress?.(nextData);
      } catch { }
    };

    poll();
    const timer = setInterval(poll, 1000);
    return () => clearInterval(timer);
  }, [mode, onProgress]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/cancel`, { method: "POST" });
    } catch { }
    onCancel?.();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(15,23,42,0.18)] p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-[28px] border border-white/80 bg-white p-8 text-center shadow-[0_28px_80px_rgba(15,23,42,0.16)]">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[#eff4ff]">
          <Spinner size="xl" color="info" />
        </div>

        <h3 className="mt-6 text-xl font-semibold text-[#101828]">Scanning look-alike domains</h3>
        <p className="mt-2 text-sm leading-6 text-[#667085]">
          {data.status || (mode === "ws" ? "Receiving live progress updates." : "Realtime channel unavailable. Polling progress instead.")}
        </p>

        <div className="mt-7 overflow-hidden rounded-full bg-[#eef2f6]">
          <div
            className="h-2.5 rounded-full bg-[#335cff] transition-all duration-500"
            style={{ width: `${data.percent}%` }}
          />
        </div>

        <div className="mt-5 text-4xl font-semibold tracking-tight text-[#101828]">
          {Math.round(data.percent)}
          <span className="ml-1 text-xl text-[#98a2b3]">%</span>
        </div>

        <button
          type="button"
          onClick={handleCancel}
          disabled={cancelling}
          className="mt-7 inline-flex w-full items-center justify-center rounded-2xl border border-[#fecaca] bg-[#fef2f2] px-4 py-3 text-sm font-semibold text-[#b42318] transition-colors hover:bg-[#fee4e2] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {cancelling ? "Stopping..." : "Cancel Scan"}
        </button>
      </div>
    </div>
  );
}
