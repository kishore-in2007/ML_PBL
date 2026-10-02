import React, { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../../api/api";
import { formatDate, mediaUrl, percent } from "../../api/helpers";
import AppShell, { EmptyState, StatCard } from "../../components/AppShell";
import { Activity, Image as ImageIcon, TrendingUp } from "lucide-react";

export default function RecoveryTrends() {
  const [logs, setLogs] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/patients/me/daily-wound-logs"), api.get("/patients/me/recovery-overview")])
      .then(([logsResponse, overviewResponse]) => {
        setLogs(logsResponse.data || []);
        setOverview(overviewResponse.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const chartData = useMemo(
    () =>
      logs
        .slice()
        .reverse()
        .map((log) => ({
          date: formatDate(log.log_date),
          healing: log.healing_rate ?? 0,
          area: log.wound_area_cm2 ?? 0,
        })),
    [logs]
  );

  const latest = overview?.latest_daily_log || logs[0];

  return (
    <AppShell role="patient" title="Recovery Trends">
      {loading ? (
        <div className="rounded-xl bg-white p-6 shadow-sm">Loading recovery trends...</div>
      ) : (
        <div className="space-y-6">
          <section className="grid gap-4 md:grid-cols-3">
            <StatCard label="Daily Uploads" value={logs.length} icon={ImageIcon} />
            <StatCard label="Latest Healing Rate" value={percent(latest?.healing_rate)} tone="good" icon={TrendingUp} />
            <StatCard label="Latest Trend" value={latest?.healing_trend || "No data"} icon={Activity} />
          </section>

          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-[#061907]">Healing rate and wound area</h2>
            <div className="mt-6 h-[340px]">
              {chartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 24, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e4dfd7" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line yAxisId="left" type="monotone" dataKey="healing" name="Healing rate" stroke="#4e644c" strokeWidth={3} dot={{ r: 4 }} />
                    <Line yAxisId="right" type="monotone" dataKey="area" name="Wound area cm²" stroke="#c56d3f" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No trend data yet" message="Upload daily photos to build your recovery chart." />
              )}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {logs.map((log) => (
              <article key={log.id} className="rounded-xl border border-[#e4dfd7] bg-white p-4 shadow-sm">
                <img src={mediaUrl(log.mask_overlay_url || log.image_url)} alt="Daily wound log" className="h-48 w-full rounded-lg bg-[#f8f4ee] object-cover" />
                <div className="mt-4 flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-[#061907]">{formatDate(log.log_date)}</p>
                    <p className="text-sm text-[#667064]">{log.risk_class || "No risk class"} • {log.doctor_review_status}</p>
                  </div>
                  <span className="rounded-full bg-[#ebf2ec] px-3 py-1 text-sm font-bold text-[#061907]">{percent(log.healing_rate)}</span>
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
    </AppShell>
  );
}
