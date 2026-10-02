import React, { useEffect, useState } from "react";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell from "../../components/AppShell";

const emptyProfile = {
  surgery_type: "",
  surgery_date: "",
  date_of_birth: "",
  phone_number: "",
  reference_marker_cm: 2,
  next_appointment_date: "",
  doctor_consultancy_date: "",
  final_doctor_meet_date: "",
  recovery_goal: "",
};

export default function PatientProfile() {
  const [form, setForm] = useState(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/patients/me")
      .then((response) => {
        const patient = response.data;
        setForm({
          surgery_type: patient.surgery_type || "",
          surgery_date: toLocalInput(patient.surgery_date),
          date_of_birth: patient.date_of_birth || "",
          phone_number: patient.phone_number || "",
          reference_marker_cm: patient.reference_marker_cm || 2,
          next_appointment_date: toLocalInput(patient.next_appointment_date),
          doctor_consultancy_date: toLocalInput(patient.doctor_consultancy_date),
          final_doctor_meet_date: toLocalInput(patient.final_doctor_meet_date),
          recovery_goal: patient.recovery_goal || "",
        });
      })
      .catch((err) => setError(err.response?.data?.detail || "Unable to load profile."))
      .finally(() => setLoading(false));
  }, []);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    const payload = {
      ...form,
      reference_marker_cm: Number(form.reference_marker_cm) || 2,
      surgery_date: fromLocalInput(form.surgery_date),
      next_appointment_date: fromLocalInput(form.next_appointment_date),
      doctor_consultancy_date: fromLocalInput(form.doctor_consultancy_date),
      final_doctor_meet_date: fromLocalInput(form.final_doctor_meet_date),
    };

    try {
      await api.put("/patients/me", payload);
      setMessage("Profile saved successfully.");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to save profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell role="patient" title="Patient Profile">
      {loading ? (
        <div className="rounded-xl bg-white p-6 shadow-sm">Loading profile...</div>
      ) : (
        <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-[#061907]">Recovery details</h2>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <Field label="Surgery type" value={form.surgery_type} onChange={(value) => update("surgery_type", value)} />
              <Field label="Date of birth" type="date" value={form.date_of_birth} onChange={(value) => update("date_of_birth", value)} />
              <Field label="Phone number" value={form.phone_number} onChange={(value) => update("phone_number", value)} />
              <Field label="Reference marker cm" type="number" step="0.1" value={form.reference_marker_cm} onChange={(value) => update("reference_marker_cm", value)} />
              <Field label="Surgery date" type="datetime-local" value={form.surgery_date} onChange={(value) => update("surgery_date", value)} />
              <Field label="Next appointment date" type="datetime-local" value={form.next_appointment_date} onChange={(value) => update("next_appointment_date", value)} />
              <Field label="Doctor consultancy date" type="datetime-local" value={form.doctor_consultancy_date} onChange={(value) => update("doctor_consultancy_date", value)} />
              <Field label="Final doctor meet date" type="datetime-local" value={form.final_doctor_meet_date} onChange={(value) => update("final_doctor_meet_date", value)} />
            </div>
            <label className="mt-4 block">
              <span className="text-sm font-semibold text-[#4d574b]">Recovery goal</span>
              <textarea
                rows="4"
                value={form.recovery_goal}
                onChange={(event) => update("recovery_goal", event.target.value)}
                className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm focus:border-[#061907] focus:ring-[#061907]"
              />
            </label>
            {message && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
            {error && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
            <button disabled={saving} className="mt-5 rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white disabled:opacity-60">
              {saving ? "Saving..." : "Save Profile"}
            </button>
          </section>

          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <h3 className="text-lg font-bold text-[#061907]">Stored appointment timeline</h3>
            <div className="mt-5 space-y-4">
              <Summary label="Surgery" value={formatDateTime(fromLocalInput(form.surgery_date))} />
              <Summary label="Next Appointment" value={formatDateTime(fromLocalInput(form.next_appointment_date))} />
              <Summary label="Doctor Consultancy" value={formatDateTime(fromLocalInput(form.doctor_consultancy_date))} />
              <Summary label="Final Doctor Meet" value={formatDateTime(fromLocalInput(form.final_doctor_meet_date))} />
            </div>
          </section>
        </form>
      )}
    </AppShell>
  );
}

function Field({ label, value, onChange, type = "text", step }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-[#4d574b]">{label}</span>
      <input
        type={type}
        step={step}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm focus:border-[#061907] focus:ring-[#061907]"
      />
    </label>
  );
}

function Summary({ label, value }) {
  return (
    <div className="rounded-lg bg-[#f8f4ee] p-4">
      <p className="text-sm font-semibold text-[#667064]">{label}</p>
      <p className="mt-1 font-bold text-[#061907]">{value}</p>
    </div>
  );
}

function toLocalInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 16);
}

function fromLocalInput(value) {
  return value ? new Date(value).toISOString() : null;
}
