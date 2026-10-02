import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../api/api";
import { formatDateTime, mediaUrl, percent } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function PatientRecords() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/doctor/patients")
      .then((response) => setPatients(response.data || []))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load patients."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell role="doctor" title="Patient Records">
      {loading && <div className="rounded-xl bg-white p-6 shadow-sm">Loading assigned patients...</div>}
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
      {!loading && !error && (
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <div>
              <h2 className="text-xl font-bold text-[#061907]">Patients under maintenance</h2>
              <p className="text-sm text-[#667064]">Latest wound status, healing rate, appointment, and review queue.</p>
            </div>
          </div>
          <div className="space-y-4">
            {patients.length ? (
              patients.map((item) => (
                <article key={item.patient.id} className="grid gap-4 rounded-xl border border-[#e4dfd7] p-4 lg:grid-cols-[120px_1fr_auto] lg:items-center">
                  <img
                    src={mediaUrl(item.latest_image_url)}
                    alt="Latest patient wound"
                    className="h-28 w-full rounded-lg bg-[#f8f4ee] object-cover lg:w-28"
                  />
                  <div className="grid gap-3 md:grid-cols-4">
                    <Cell label="Patient ID" value={item.patient.id} />
                    <Cell label="Surgery" value={item.patient.surgery_type || "Not set"} />
                    <Cell label="Risk" value={item.latest_risk_class || "No upload"} />
                    <Cell label="Healing" value={percent(item.healing_rate)} />
                    <Cell label="Trend" value={item.healing_trend || "--"} />
                    <Cell label="Open Triage" value={item.open_triage_cases} />
                    <Cell label="Next Appointment" value={item.next_appointment ? formatDateTime(item.next_appointment.scheduled_start) : "Not set"} />
                    <Cell label="Last Upload" value={item.patient.last_daily_upload_at ? formatDateTime(item.patient.last_daily_upload_at) : "None"} />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Link to={`/doctor/patient-summary?patient_id=${item.patient.id}`} className="rounded-lg bg-[#061907] px-4 py-2 text-center text-sm font-bold text-white">
                      Summary
                    </Link>
                    {item.latest_image_id && (
                      <Link to={`/doctor/wound-review?image_id=${item.latest_image_id}&patient_id=${item.patient.id}`} className="rounded-lg border border-[#061907] px-4 py-2 text-center text-sm font-bold text-[#061907]">
                        Review Image
                      </Link>
                    )}
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No assigned patients" message="Assigned patients will appear after doctor-patient assignment is created." />
            )}
          </div>
        </section>
      )}
    </AppShell>
  );
}

function Cell({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-[#667064]">{label}</p>
      <p className="mt-1 break-words text-sm font-bold text-[#061907]">{value}</p>
    </div>
  );
}
