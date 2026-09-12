"use client";

import { useEffect, useState } from "react";

type DashboardState = {
  mode: "RESEARCH" | "LIVE";
  live_trading_allowed: boolean;
  execution_mode: string;
  risk_gate: string;
  high_volatility_policy: string;
  read_only: boolean;
  as_of: string;
};

const fallbackState: DashboardState = {
  mode: "RESEARCH",
  live_trading_allowed: false,
  execution_mode: "PAPER_FIRST",
  risk_gate: "REQUIRED",
  high_volatility_policy: "BLOCKED_BY_DEFAULT",
  read_only: true,
  as_of: "",
};

export default function DashboardStatePanel() {
  const [state, setState] = useState<DashboardState>(fallbackState);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/dashboard/state", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("dashboard API unavailable");
        return response.json() as Promise<DashboardState>;
      })
      .then((payload) => {
        if (active) {
          setState(payload);
          setConnected(true);
        }
      })
      .catch(() => {
        if (active) setConnected(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <article className="panel api-panel" aria-label="Runtime dashboard state">
      <div className="panel-heading">
        <div>
          <p className="section-label">RUNTIME API</p>
          <h2>{state.mode === "LIVE" ? "Live authorized" : "Research mode"}</h2>
        </div>
        <span className="badge">{connected ? "CONNECTED" : "FALLBACK"}</span>
      </div>
      <p className="muted">
        {connected
          ? "State is sourced from the versioned backend dashboard contract."
          : "Backend state is unavailable; the UI remains fail-safe and read-only."}
      </p>
      <div className="metric-row">
        <div><span className="metric-label">Execution</span><strong>{state.execution_mode}</strong></div>
        <div><span className="metric-label">Risk gate</span><strong>{state.risk_gate}</strong></div>
        <div><span className="metric-label">Live allowed</span><strong>{state.live_trading_allowed ? "YES" : "NO"}</strong></div>
      </div>
    </article>
  );
}
