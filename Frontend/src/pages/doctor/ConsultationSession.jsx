import React, { useEffect, useState } from "react";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function ConsultationSession() {
  const [sessions, setSessions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({ patient_id: "", appointment_id: "", connection_url: "" });

  const load = () => {
    setLoading(true);
    Promise.all([api.get("/doctor/sessions"), api.get("/doctor/patients"), api.get("/doctor/appointments")])
      .then(([sessionResponse, patientResponse, appointmentResponse]) => {
        setSessions(sessionResponse.data || []);
        setPatients(patientResponse.data || []);
        setAppointments(appointmentResponse.data || []);
        const firstPatient = patientResponse.data?.[0]?.patient?.id;
        if (firstPatient) setForm((current) => ({ ...current, patient_id: current.patient_id || firstPatient }));
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const createSession = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.post("/doctor/sessions", {
        patient_id: form.patient_id,
        appointment_id: form.appointment_id || null,
        connection_url: form.connection_url || null,
      });
      setMessage("Consultation session created.");
      setForm((current) => ({ ...current, appointment_id: "", connection_url: "" }));
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to create consultation session.");
    }
  };

  const closeSession = async (session, summary) => {
    await api.patch(`/doctor/sessions/${session.id}`, { session_status: "completed", summary });
    load();
  };

  return (
    <AppShell role="doctor" title="One-on-One Sessions">
      <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-[#061907]">Create session connection</h2>
          <form onSubmit={createSession} className="mt-5 space-y-4">
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Patient</span>
              <select value={form.patient_id} onChange={(e) => update("patient_id", e.target.value)} required className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm">
                <option value="">Select patient</option>
                {patients.map((item) => (
                  <option key={item.patient.id} value={item.patient.id}>
                    {item.patient.id} {item.patient.surgery_type ? `- ${item.patient.surgery_type}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Linked appointment</span>
              <select value={form.appointment_id} onChange={(e) => update("appointment_id", e.target.value)} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm">
                <option value="">No linked appointment</option>
                {appointments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {formatDateTime(item.scheduled_start)} - {item.patient_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Connection URL</span>
              <input value={form.connection_url} onChange={(e) => update("connection_url", e.target.value)} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" placeholder="https://meet.example/session" />
            </label>
            {message && <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
            {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
            <button disabled={!patients.length} className="w-full rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white disabled:opacity-60">
              Create Session
            </button>
          </form>
        </section>

        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-[#061907]">Session dashboard</h2>
          <div className="mt-5 space-y-3">
            {loading ? (
              <div>Loading sessions...</div>
            ) : sessions.length ? (
              sessions.map((session) => (
                <SessionCard key={session.id} session={session} onClose={closeSession} />
              ))
            ) : (
              <EmptyState title="No sessions" message="Create a one-on-one connection for a patient appointment." />
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function SessionCard({ session, onClose }) {
  const [summary, setSummary] = useState(session.summary || "");
  return (
    <article className="rounded-lg border border-[#e4dfd7] p-4">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
        <div>
          <p className="font-bold text-[#061907]">Patient {session.patient_id}</p>
          <p className="text-sm text-[#667064]">{session.session_status} • Created {formatDateTime(session.created_at)}</p>
          {session.connection_url && (
            <a href={session.connection_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex text-sm font-bold text-[#061907] hover:underline">
              Open connection
            </a>
          )}
        </div>
      </div>
      <textarea value={summary} onChange={(e) => setSummary(e.target.value)} rows="3" className="mt-3 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" placeholder="Session summary for patient record" />
      <button onClick={() => onClose(session, summary)} className="mt-3 rounded-lg border border-[#061907] px-4 py-2 text-sm font-bold text-[#061907]">
        Save Summary and Complete
      </button>
    </article>
  );
}
