import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function UrgentAlerts() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/doctor/dashboard")
      .then((response) => setDashboard(response.data))
      .finally(() => setLoading(false));
  }, []);

  const cases = dashboard?.priority_cases || [];
  const urgentNotifications = (dashboard?.notifications || []).filter((item) => item.priority === "urgent" || item.priority === "high");

  return (
    <AppShell role="doctor" title="Urgent Alerts">
      {loading ? (
        <div className="rounded-xl bg-white p-6 shadow-sm">Loading urgent alerts...</div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-xl border border-red-100 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-[#061907]">Emergency and high-risk cases</h2>
            <div className="mt-5 space-y-3">
              {cases.length ? (
                cases.map((item) => (
                  <article key={item.id} className="rounded-lg border border-red-200 bg-red-50 p-4">
                    <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                      <div>
                        <p className="font-bold text-red-900">{item.risk_class}</p>
                        <p className="text-sm text-red-800">Patient {item.patient_id} • Score {Number(item.final_risk_score).toFixed(1)} • {item.status}</p>
                        <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-red-700">{formatDateTime(item.created_at)}</p>
                      </div>
                      <Link to={`/doctor/patient-summary?patient_id=${item.patient_id}`} className="rounded-lg bg-red-700 px-4 py-2 text-center text-sm font-bold text-white">
                        Handle Case
                      </Link>
                    </div>
                  </article>
                ))
              ) : (
                <EmptyState title="No urgent cases" message="The backend has no escalated triage cases right now." />
              )}
            </div>
          </section>

          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-[#061907]">High-priority notifications</h2>
            <div className="mt-5 space-y-3">
              {urgentNotifications.length ? (
                urgentNotifications.map((item) => (
                  <article key={item.id} className="rounded-lg bg-[#fff4ec] p-4">
                    <p className="font-bold text-[#061907]">{item.title}</p>
                    <p className="mt-1 text-sm text-[#667064]">{item.message || "No message"}</p>
                  </article>
                ))
              ) : (
                <EmptyState title="No high-priority notifications" message="Urgent notification records will appear here." />
              )}
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
