import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../../api/api";
import { formatDateTime, mediaUrl, number, percent } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function PatientSummary() {
  const [searchParams] = useSearchParams();
  const patientId = searchParams.get("patient_id");
  const [summary, setSummary] = useState(null);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    const request = patientId ? api.get(`/doctor/patients/${patientId}/summary`) : api.get("/doctor/patients");
    request
      .then((response) => {
        if (patientId) setSummary(response.data);
        else setPatients(response.data || []);
      })
      .catch((err) => setError(err.response?.data?.detail || "Unable to load patient summary."))
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <AppShell role="doctor" title="Patient Summary">
      {loading && <div className="rounded-xl bg-white p-6 shadow-sm">Loading patient summary...</div>}
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      {!loading && !error && !patientId && (
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-[#061907]">Choose a patient</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {patients.length ? (
              patients.map((item) => (
                <Link key={item.patient.id} to={`/doctor/patient-summary?patient_id=${item.patient.id}`} className="rounded-xl border border-[#e4dfd7] p-4 hover:bg-[#f8f4ee]">
                  <p className="font-bold text-[#061907]">Patient {item.patient.id}</p>
                  <p className="mt-1 text-sm text-[#667064]">{item.patient.surgery_type || "Surgery not set"} • {item.latest_risk_class || "No upload"}</p>
                </Link>
              ))
            ) : (
              <EmptyState title="No patients assigned" message="Assigned patient summaries will appear here." />
            )}
          </div>
        </section>
      )}

      {!loading && !error && summary && (
        <div className="space-y-6">
          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <div className="grid gap-6 lg:grid-cols-[220px_1fr_auto]">
              <img src={mediaUrl(summary.latest_image_url)} alt="Latest wound" className="h-52 w-full rounded-lg bg-[#f8f4ee] object-cover" />
              <div>
                <h2 className="text-2xl font-bold text-[#061907]">Patient {summary.patient.id}</h2>
                <p className="mt-1 text-sm text-[#667064]">{summary.patient.surgery_type || "Surgery type not set"}</p>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Healing Rate" value={percent(summary.healing_rate)} />
                  <Metric label="Trend" value={summary.healing_trend || "--"} />
                  <Metric label="Latest Risk" value={summary.latest_risk_class || "--"} />
                  <Metric label="Open Triage" value={summary.open_triage_cases} />
                </div>
              </div>
              {summary.latest_image_id && (
                <Link to={`/doctor/wound-review?image_id=${summary.latest_image_id}&patient_id=${summary.patient.id}`} className="h-fit rounded-lg bg-[#061907] px-5 py-3 text-center text-sm font-bold text-white">
                  Review Latest Image
                </Link>
              )}
            </div>
          </section>

          <section className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-[#061907]">Patient record</h3>
              <div className="mt-4 space-y-3">
                <Metric label="Phone" value={summary.patient.phone_number || "--"} />
                <Metric label="Surgery Date" value={summary.patient.surgery_date ? formatDateTime(summary.patient.surgery_date) : "Not set"} />
                <Metric label="Doctor Consultancy" value={summary.patient.doctor_consultancy_date ? formatDateTime(summary.patient.doctor_consultancy_date) : "Not set"} />
                <Metric label="Final Doctor Meet" value={summary.patient.final_doctor_meet_date ? formatDateTime(summary.patient.final_doctor_meet_date) : "Not set"} />
              </div>
            </div>

            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-[#061907]">Clinical context</h3>
              <div className="mt-4 space-y-3">
                <Metric label="Latest Wound Area" value={number(summary.latest_wound_area_cm2, " cm²")} />
                <Metric label="Confidence" value={summary.latest_confidence ? `${(summary.latest_confidence * 100).toFixed(1)}%` : "--"} />
                <Metric label="Next Appointment" value={summary.next_appointment ? formatDateTime(summary.next_appointment.scheduled_start) : "Not scheduled"} />
                <Metric label="Recovery Goal" value={summary.patient.recovery_goal || "--"} />
              </div>
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
      <p className="mt-1 break-words font-bold text-[#061907]">{value}</p>
    </div>
  );
}
