import React, { useEffect, useMemo, useState } from "react";
import { CalendarPlus } from "lucide-react";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    patient_id: "",
    scheduled_start: "",
    scheduled_end: "",
    appointment_type: "video",
    reason: "",
    meeting_url: "",
  });

  const patientOptions = useMemo(() => patients.map((item) => item.patient), [patients]);

  const load = () => {
    setLoading(true);
    Promise.all([api.get("/doctor/appointments"), api.get("/doctor/patients")])
      .then(([appointmentResponse, patientResponse]) => {
        setAppointments(appointmentResponse.data || []);
        setPatients(patientResponse.data || []);
        const firstPatient = patientResponse.data?.[0]?.patient?.id;
        if (firstPatient) setForm((current) => ({ ...current, patient_id: current.patient_id || firstPatient }));
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await api.post("/doctor/appointments", {
        ...form,
        scheduled_start: new Date(form.scheduled_start).toISOString(),
        scheduled_end: new Date(form.scheduled_end).toISOString(),
      });
      setMessage("Appointment created successfully.");
      setForm((current) => ({ ...current, scheduled_start: "", scheduled_end: "", reason: "", meeting_url: "" }));
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to create appointment. Check patient and timing conflict.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell role="doctor" title="Appointments">
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#ebf2ec] p-3 text-[#061907]">
              <CalendarPlus size={22} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#061907]">Fix patient appointment</h2>
              <p className="text-sm text-[#667064]">Backend validates doctor timing conflicts before saving.</p>
            </div>
          </div>

          <form onSubmit={submit} className="mt-5 space-y-4">
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Patient</span>
              <select value={form.patient_id} onChange={(e) => update("patient_id", e.target.value)} required className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm">
                <option value="">Select patient</option>
                {patientOptions.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.id} {patient.surgery_type ? `- ${patient.surgery_type}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Start" type="datetime-local" value={form.scheduled_start} onChange={(value) => update("scheduled_start", value)} />
              <Field label="End" type="datetime-local" value={form.scheduled_end} onChange={(value) => update("scheduled_end", value)} />
            </div>
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Type</span>
              <select value={form.appointment_type} onChange={(e) => update("appointment_type", e.target.value)} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm">
                <option value="video">Video</option>
                <option value="in_person">In person</option>
                <option value="phone">Phone</option>
              </select>
            </label>
            <Field label="Meeting URL" value={form.meeting_url} onChange={(value) => update("meeting_url", value)} />
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Reason</span>
              <textarea value={form.reason} onChange={(e) => update("reason", e.target.value)} rows="4" className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" />
            </label>
            {message && <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
            {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
            <button disabled={saving || !patientOptions.length} className="w-full rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white disabled:opacity-60">
              {saving ? "Creating..." : "Create Appointment"}
            </button>
          </form>
        </section>

        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-[#061907]">Doctor schedule</h2>
          <div className="mt-5 space-y-3">
            {loading ? (
              <div>Loading appointments...</div>
            ) : appointments.length ? (
              appointments.map((item) => (
                <article key={item.id} className="rounded-lg border border-[#e4dfd7] p-4">
                  <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                    <div>
                      <p className="font-bold text-[#061907]">{formatDateTime(item.scheduled_start)}</p>
                      <p className="text-sm text-[#667064]">Patient {item.patient_id} • {item.appointment_type} • {item.status}</p>
                      <p className="mt-1 text-sm text-[#4d574b]">{item.reason || "No reason entered"}</p>
                    </div>
                    {item.meeting_url && (
                      <a href={item.meeting_url} target="_blank" rel="noreferrer" className="rounded-lg border border-[#061907] px-4 py-2 text-center text-sm font-bold text-[#061907]">
                        Open Session
                      </a>
                    )}
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No appointments" message="Create the first appointment for an assigned patient." />
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function Field({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-[#4d574b]">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" />
    </label>
  );
}
