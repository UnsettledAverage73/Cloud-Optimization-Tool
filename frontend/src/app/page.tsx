"use client";

import React, { useState, useEffect } from "react";
import {
  Server,
  Activity,
  DollarSign,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Power,
  Shield,
  Clock,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

interface TargetNode {
  id: string;
  instance_id: string;
  name: string;
  provider: string;
  public_ip: string;
  instance_type: string;
  region: string;
  state: string;
}

interface AnalysisReport {
  instance_id: string;
  instance_type: string;
  idle_ratio: number;
  avg_load_1m: number;
  avg_connections: number;
  recommendation: "STOP" | "KEEP_RUNNING";
  cost_analysis: {
    monthly_projected_savings_usd: number;
  };
}

interface TelemetryPoint {
  time: string;
  load_1m: number;
  active_tcp_connections: number;
  is_idle: boolean;
}

export default function Dashboard() {
  const [nodes, setNodes] = useState<TargetNode[]>([]);
  const [reports, setReports] = useState<Record<string, AnalysisReport>>({});
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [dryRunMode, setDryRunMode] = useState(true);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const nodesRes = await fetch("/api/v1/nodes");
      if (!nodesRes.ok) {
        throw new Error(`Nodes API HTTP ${nodesRes.status}`);
      }
      const nodesData: TargetNode[] = await nodesRes.json();
      setNodes(Array.isArray(nodesData) ? nodesData : []);

      if (Array.isArray(nodesData) && nodesData.length > 0 && !selectedNode) {
        setSelectedNode(nodesData[0].instance_id);
      }

      const analyzeRes = await fetch("/api/v1/analyze?window_minutes=15", {
        method: "POST",
      });
      if (!analyzeRes.ok) {
        const errorData = await analyzeRes.json().catch(() => ({}));
        throw new Error(
          errorData.message || errorData.error || `Analyze API HTTP ${analyzeRes.status}`
        );
      }
      const analyzeData = await analyzeRes.json();

      const reportMap: Record<string, AnalysisReport> = {};
      if (analyzeData && analyzeData.reports) {
        analyzeData.reports.forEach((r: AnalysisReport) => {
          reportMap[r.instance_id] = r;
        });
      }
      setReports(reportMap);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
      setMessage({
        type: "error",
        text: "Could not connect to OptiScale FastAPI engine. Ensure backend is active on http://127.0.0.1:8000.",
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchTelemetryHistory = async (instanceId: string) => {
    try {
      const res = await fetch(`/api/v1/telemetry/${instanceId}?limit=30`);
      if (!res.ok) {
        throw new Error(`Telemetry API HTTP ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        const formatted = data
          .map((t: any) => ({
            time: new Date(t.time).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            }),
            load_1m: t.load_1m,
            active_tcp_connections: t.active_tcp_connections,
            is_idle: t.is_idle,
          }))
          .reverse();
        setTelemetry(formatted);
      } else {
        setTelemetry([]);
      }
    } catch (err) {
      console.error("Failed to fetch telemetry history:", err);
      setTelemetry([]);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      fetchTelemetryHistory(selectedNode);
    }
  }, [selectedNode]);

  const handleRemediate = async (instanceId: string) => {
    setActionLoading(instanceId);
    setMessage(null);
    try {
      const res = await fetch(`/api/v1/remediate/${instanceId}?dry_run=${dryRunMode}`, {
        method: "POST",
      });
      const data = await res.json();

      if (res.ok) {
        const text = dryRunMode
          ? `[DRY-RUN PASSED] Shutdown action validated for ${instanceId}.`
          : `[LIVE REMEDIATION] Node ${instanceId} power-down command issued.`;
        setMessage({ type: "success", text });
        fetchDashboardData();
      } else {
        setMessage({ type: "error", text: data.detail || "Remediation failed." });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Error executing remediation request." });
    } finally {
      setActionLoading(null);
    }
  };

  const totalWaste = Object.values(reports).reduce(
    (acc, r) => acc + (r.recommendation === "STOP" ? r.cost_analysis?.monthly_projected_savings_usd || 0 : 0),
    0
  );
  const idleCount = Object.values(reports).filter((r) => r.recommendation === "STOP").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6" suppressHydrationWarning>
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Activity className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">OptiScale Dashboard</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">Autonomous Cloud Cost Optimization & Telemetry Control Plane</p>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setDryRunMode(!dryRunMode)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              dryRunMode
                ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
            }`}
          >
            <Shield className="w-4 h-4" />
            {dryRunMode ? "Mode: DRY-RUN (Safe)" : "Mode: LIVE (Active)"}
          </button>

          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-lg text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg text-xs font-mono border flex items-center gap-3 ${
            message.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-rose-950/40 border-rose-500/40 text-rose-300"
          }`}
        >
          {message.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Total Discovered Nodes</span>
            <Server className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-2xl font-bold text-white">{nodes.length}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Idle Candidates (STOP)</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{idleCount}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Projected Monthly Waste</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">${totalWaste.toFixed(2)} USD</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Layer 1 Ingestion Status</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-sm font-semibold text-emerald-400 flex items-center gap-2 mt-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            TimescaleDB Live
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Server className="w-4 h-4 text-indigo-400" />
            Target Infrastructure Registry
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="p-3">Node Name / ID</th>
                  <th className="p-3">IP / Type</th>
                  <th className="p-3">Idle Ratio</th>
                  <th className="p-3">Recommendation</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {nodes.map((node) => {
                  const report = reports[node.instance_id];
                  const isSelected = selectedNode === node.instance_id;

                  return (
                    <tr
                      key={node.id}
                      onClick={() => setSelectedNode(node.instance_id)}
                      className={`cursor-pointer transition hover:bg-slate-800/40 ${
                        isSelected ? "bg-slate-800/70 border-l-2 border-indigo-500" : ""
                      }`}
                    >
                      <td className="p-3">
                        <div className="font-semibold text-white">{node.name}</div>
                        <div className="text-[10px] font-mono text-slate-500">{node.instance_id}</div>
                      </td>
                      <td className="p-3 font-mono">
                        <div>{node.public_ip}</div>
                        <div className="text-[10px] text-slate-500">{node.instance_type}</div>
                      </td>
                      <td className="p-3">
                        {report ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="bg-amber-400 h-1.5 rounded-full"
                                style={{ width: `${(report.idle_ratio * 100).toFixed(0)}%` }}
                              ></div>
                            </div>
                            <span className="font-mono text-[11px]">{(report.idle_ratio * 100).toFixed(0)}%</span>
                          </div>
                        ) : (
                          <span className="text-slate-600">Pending</span>
                        )}
                      </td>
                      <td className="p-3">
                        {report?.recommendation === "STOP" ? (
                          <span className="bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
                            CANDIDATE: STOP
                          </span>
                        ) : (
                          <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
                            KEEP RUNNING
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemediate(node.instance_id);
                          }}
                          disabled={actionLoading === node.instance_id}
                          className="bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 border border-rose-500/40 px-3 py-1 rounded text-xs font-medium flex items-center gap-1 ml-auto transition"
                        >
                          <Power className="w-3 h-3" />
                          {actionLoading === node.instance_id ? "Executing..." : "Stop Node"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-1 flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" />
            TimescaleDB Telemetry Window
          </h2>
          <p className="text-xs text-slate-400 mb-4 font-mono">Instance: {selectedNode || "None"}</p>

          {telemetry.length > 0 ? (
            <div className="space-y-6">
              <div>
                <div className="text-xs font-semibold text-slate-300 mb-2">1-Min CPU Load Average</div>
                <div className="h-40 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={telemetry}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} domain={[0, "auto"]} />
                      <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }} />
                      <Line type="monotone" dataKey="load_1m" stroke="#818cf8" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-300 mb-2">Active TCP Connections</div>
                <div className="h-40 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={telemetry}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} allowDecimals={false} />
                      <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }} />
                      <Line type="monotone" dataKey="active_tcp_connections" stroke="#34d399" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-xs text-slate-500">
              No historical telemetry ticks found for this instance.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
