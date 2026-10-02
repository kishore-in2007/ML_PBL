import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, CalendarDays, ClipboardCheck, UsersRound } from "lucide-react";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState, StatCard } from "../../components/AppShell";

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/doctor/dashboard")
      .then((response) => setDashboard(response.data))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load doctor dashboard."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell role="doctor" title="Clinical Dashboard">
      {loading && <div className="rounded-xl bg-white p-6 shadow-sm">Loading clinical dashboard...</div>}
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      {!loading && !error && dashboard && (
        <div className="space-y-6">
          <section className="grid gap-4 md:grid-cols-5">
            <StatCard label="Patients" value={dashboard.total_patients} icon={UsersRound} />
            <StatCard label="Active Cases" value={dashboard.active_recovery_cases} tone="good" icon={ClipboardCheck} />
            <StatCard label="Today's Appointments" value={dashboard.todays_appointments} icon={CalendarDays} />
            <StatCard label="Urgent Alerts" value={dashboard.urgent_alerts} tone={dashboard.urgent_alerts ? "danger" : "default"} icon={AlertTriangle} />
            <StatCard label="Pending Reviews" value={dashboard.pending_reviews} tone={dashboard.pending_reviews ? "warn" : "default"} />
          </section>

          <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <div className="mb-5 flex items-center justify-between gap-3">
                <h2 className="text-xl font-bold text-[#061907]">Priority cases</h2>
                <Link to="/doctor/urgent-alerts" className="text-sm font-bold text-[#061907] hover:underline">View alerts</Link>
              </div>
              <div className="space-y-3">
                {dashboard.priority_cases?.length ? (
                  dashboard.priority_cases.map((item) => (
                    <article key={item.id} className="flex flex-col gap-3 rounded-lg border border-red-100 bg-red-50 p-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="font-bold text-[#061907]">Patient {item.patient_id}</p>
                        <p className="text-sm text-[#667064]">{item.risk_class} • Score {Number(item.final_risk_score).toFixed(1)} • {item.status}</p>
                      </div>
                      <button
                        onClick={() => navigate(`/doctor/patient-summary?patient_id=${item.patient_id}`)}
                        className="rounded-lg bg-[#061907] px-4 py-2 text-sm font-bold text-white"
                      >
                        Open Patient
                      </button>
                    </article>
                  ))
                ) : (
                  <EmptyState title="No urgent cases" message="Escalated triage cases will appear here." />
                )}
              </div>
            </div>

            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <div className="mb-5 flex items-center justify-between gap-3">
                <h2 className="text-xl font-bold text-[#061907]">Upcoming appointments</h2>
                <Link to="/doctor/appointments" className="text-sm font-bold text-[#061907] hover:underline">Schedule</Link>
              </div>
              <div className="space-y-3">
                {dashboard.upcoming_appointments?.length ? (
                  dashboard.upcoming_appointments.map((item) => (
                    <article key={item.id} className="rounded-lg bg-[#f8f4ee] p-4">
                      <p className="font-bold text-[#061907]">{formatDateTime(item.scheduled_start)}</p>
                      <p className="text-sm text-[#667064]">{item.appointment_type} • {item.status}</p>
                      <p className="mt-1 text-sm text-[#4d574b]">{item.reason || "No reason entered"}</p>
                    </article>
                  ))
                ) : (
                  <EmptyState title="No appointments" message="Created appointments will show in this schedule." />
                )}
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="text-xl font-bold text-[#061907]">Recent notifications</h2>
              <Link to="/doctor/notifications" className="text-sm font-bold text-[#061907] hover:underline">Open inbox</Link>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {dashboard.notifications?.length ? (
                dashboard.notifications.slice(0, 4).map((item) => (
                  <article key={item.id} className="rounded-lg border border-[#e4dfd7] p-4">
                    <p className="font-bold text-[#061907]">{item.title}</p>
                    <p className="mt-1 text-sm text-[#667064]">{item.message || "No message"}</p>
                  </article>
                ))
              ) : (
                <EmptyState title="No notifications" message="Urgent triage and appointment events will appear here." />
              )}
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
