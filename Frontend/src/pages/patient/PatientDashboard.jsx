import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, CalendarDays, Camera, HeartPulse, ShieldCheck } from "lucide-react";
import api from "../../api/api";
import { formatDateTime, mediaUrl, percent } from "../../api/helpers";
import AppShell, { EmptyState, StatCard } from "../../components/AppShell";

export default function PatientDashboard() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/patients/me/recovery-overview")
      .then((response) => setOverview(response.data))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load your recovery dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const patient = overview?.patient;
  const latest = overview?.latest_daily_log;
  const nextAppointment = overview?.upcoming_appointments?.[0];
  const healingRate = latest?.healing_rate ?? patient?.current_healing_rate;
  const trend = latest?.healing_trend ?? patient?.current_healing_trend ?? "Not started";

  return (
    <AppShell role="patient" title="Recovery Dashboard">
      {loading && <div className="rounded-xl bg-white p-6 shadow-sm">Loading your recovery overview...</div>}
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      {!loading && !error && (
        <div className="space-y-6">
          <section className="grid gap-4 md:grid-cols-4">
            <StatCard label="Healing Rate" value={percent(healingRate)} tone="good" icon={HeartPulse} />
            <StatCard label="Current Trend" value={trend} icon={Activity} />
            <StatCard label="Latest Risk" value={latest?.risk_class || "No upload"} tone={latest?.needs_human_review ? "danger" : "default"} icon={ShieldCheck} />
            <StatCard label="Next Appointment" value={nextAppointment ? formatDateTime(nextAppointment.scheduled_start) : "Not set"} icon={CalendarDays} />
          </section>

          <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                  <p className="text-sm font-semibold text-[#667064]">Today's wound check</p>
                  <h2 className="mt-1 text-2xl font-bold text-[#061907]">Upload a daily photo for AI evaluation</h2>
                  <p className="mt-2 max-w-2xl text-sm text-[#667064]">
                    The backend compares today's wound area against yesterday's primary image and updates your healing rate for both you and your doctor.
                  </p>
                </div>
                <Link
                  to="/patient/capture"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white shadow-sm hover:bg-[#153315]"
                >
                  <Camera size={18} />
                  Capture Photo
                </Link>
              </div>

              {latest ? (
                <div className="mt-6 grid gap-4 md:grid-cols-[220px_1fr]">
                  <img
                    src={mediaUrl(latest.mask_overlay_url || latest.image_url)}
                    alt="Latest wound analysis"
                    className="h-56 w-full rounded-lg border border-[#e4dfd7] object-cover"
                  />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Metric label="Uploaded" value={formatDateTime(latest.created_at)} />
                    <Metric label="Doctor Review" value={latest.doctor_review_status} />
                    <Metric label="Wound Area" value={latest.wound_area_cm2 ? `${latest.wound_area_cm2.toFixed(2)} cm²` : "--"} />
                    <Metric label="Change vs Yesterday" value={latest.percent_change_from_previous !== null && latest.percent_change_from_previous !== undefined ? `${latest.percent_change_from_previous.toFixed(1)}%` : "--"} />
                    <Metric label="Pain Level" value={latest.pain_level !== null && latest.pain_level !== undefined ? `${latest.pain_level}/10` : "--"} />
                    <Metric label="Fever" value={latest.fever ? "Reported" : "No"} />
                  </div>
                </div>
              ) : (
                <div className="mt-6">
                  <EmptyState title="No daily wound photo yet" message="Your first upload will create the baseline for recovery tracking." />
                </div>
              )}
            </div>

            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-[#061907]">Care Plan</h3>
              <div className="mt-4 space-y-4">
                <Timeline label="Surgery" value={patient?.surgery_date ? formatDateTime(patient.surgery_date) : "Add in profile"} />
                <Timeline label="Doctor Consultancy" value={overview?.doctor_consultancy_date ? formatDateTime(overview.doctor_consultancy_date) : "Not scheduled"} />
                <Timeline label="Final Doctor Meet" value={overview?.final_doctor_meet_date ? formatDateTime(overview.final_doctor_meet_date) : "Not scheduled"} />
              </div>
              <Link to="/patient/trends" className="mt-6 inline-flex w-full justify-center rounded-lg border border-[#061907] px-4 py-3 text-sm font-bold text-[#061907] hover:bg-[#ebf2ec]">
                View Recovery Trends
              </Link>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg bg-[#f8f4ee] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#667064]">{label}</p>
      <p className="mt-1 break-words text-base font-bold text-[#061907]">{value}</p>
    </div>
  );
}

function Timeline({ label, value }) {
  return (
    <div className="border-l-2 border-[#cbdcc7] pl-4">
      <p className="text-sm font-semibold text-[#061907]">{label}</p>
      <p className="text-sm text-[#667064]">{value}</p>
    </div>
  );
}
