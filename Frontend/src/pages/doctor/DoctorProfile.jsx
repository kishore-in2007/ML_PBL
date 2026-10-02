import React, { useEffect, useState } from "react";
import api from "../../api/api";
import AppShell from "../../components/AppShell";

const emptyProfile = {
  specialization: "",
  license_number: "",
  hospital_name: "",
  phone_number: "",
  bio: "",
};

export default function DoctorProfile() {
  const [form, setForm] = useState(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/doctor/me")
      .then((response) => {
        setForm({
          specialization: response.data.specialization || "",
          license_number: response.data.license_number || "",
          hospital_name: response.data.hospital_name || "",
          phone_number: response.data.phone_number || "",
          bio: response.data.bio || "",
        });
      })
      .catch((err) => setError(err.response?.data?.detail || "Unable to load doctor profile."))
      .finally(() => setLoading(false));
  }, []);

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await api.put("/doctor/me", form);
      setMessage("Doctor profile saved successfully.");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to save doctor profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell role="doctor" title="Doctor Profile">
      {loading ? (
        <div className="rounded-xl bg-white p-6 shadow-sm">Loading doctor profile...</div>
      ) : (
        <form onSubmit={submit} className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-[#061907]">Clinical identity</h2>
          <p className="mt-1 text-sm text-[#667064]">This information is stored in the doctor profile table and used across doctor workflows.</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <Field label="Specialization" value={form.specialization} onChange={(value) => update("specialization", value)} />
            <Field label="License number" value={form.license_number} onChange={(value) => update("license_number", value)} />
            <Field label="Hospital name" value={form.hospital_name} onChange={(value) => update("hospital_name", value)} />
            <Field label="Phone number" value={form.phone_number} onChange={(value) => update("phone_number", value)} />
          </div>
          <label className="mt-4 block">
            <span className="text-sm font-semibold text-[#4d574b]">Bio</span>
            <textarea value={form.bio} onChange={(event) => update("bio", event.target.value)} rows="5" className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" />
          </label>
          {message && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
          {error && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
          <button disabled={saving} className="mt-5 rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white disabled:opacity-60">
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </form>
      )}
    </AppShell>
  );
}

function Field({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-[#4d574b]">{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" />
    </label>
  );
}
