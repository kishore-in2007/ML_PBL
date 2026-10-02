import React, { useEffect, useState } from "react";
import { Bell, Camera, Clock, Pill, Plus, RefreshCw } from "lucide-react";
import api from "../../api/api";
import AppShell, { EmptyState } from "../../components/AppShell";

const icons = {
  medication: Pill,
  wound_photo: Camera,
  dressing: RefreshCw,
  care: Bell,
};

export default function Reminders() {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", reminder_type: "care", schedule_time: "09:00", notes: "" });

  const load = () => {
    setLoading(true);
    api
      .get("/patients/me/reminders")
      .then((response) => setReminders(response.data || []))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load reminders."))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggle = async (reminder) => {
    await api.patch(`/patients/me/reminders/${reminder.id}`, { is_enabled: !reminder.is_enabled });
    load();
  };

  const create = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await api.post("/patients/me/reminders", {
        ...form,
        schedule_label: `Daily at ${form.schedule_time}`,
        is_enabled: true,
      });
      setForm({ title: "", reminder_type: "care", schedule_time: "09:00", notes: "" });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to create reminder.");
    }
  };

  return (
    <AppShell role="patient" title="Reminders">
      <div className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-[#061907]">Recovery reminders</h2>
              <p className="text-sm text-[#667064]">Medication, dressing changes, and daily wound photo timing are stored in the backend.</p>
            </div>
            <span className="rounded-full bg-[#ebf2ec] px-3 py-1 text-sm font-bold text-[#061907]">
              {reminders.filter((item) => item.is_enabled).length} enabled
            </span>
          </div>

          <div className="mt-5 space-y-3">
            {loading ? (
              <div>Loading reminders...</div>
            ) : reminders.length ? (
              reminders.map((reminder) => {
                const Icon = icons[reminder.reminder_type] || Bell;
                return (
                  <article key={reminder.id} className="flex flex-col justify-between gap-4 rounded-xl border border-[#e4dfd7] p-4 sm:flex-row sm:items-center">
                    <div className="flex items-start gap-4">
                      <div className="rounded-lg bg-[#ebf2ec] p-3 text-[#061907]">
                        <Icon size={22} />
                      </div>
                      <div>
                        <p className="font-bold text-[#061907]">{reminder.title}</p>
                        <p className="mt-1 flex items-center gap-2 text-sm text-[#667064]">
                          <Clock size={15} />
                          {reminder.schedule_label || `Daily at ${reminder.schedule_time}`}
                        </p>
                        {reminder.notes && <p className="mt-1 text-sm text-[#4d574b]">{reminder.notes}</p>}
                      </div>
                    </div>
                    <button
                      onClick={() => toggle(reminder)}
                      className={`rounded-full px-4 py-2 text-sm font-bold ${reminder.is_enabled ? "bg-[#061907] text-white" : "bg-[#f3efe8] text-[#667064]"}`}
                    >
                      {reminder.is_enabled ? "Enabled" : "Disabled"}
                    </button>
                  </article>
                );
              })
            ) : (
              <EmptyState title="No reminders" message="Add a care reminder to keep recovery on schedule." />
            )}
          </div>
        </section>

        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#ebf2ec] p-3 text-[#061907]">
              <Plus size={22} />
            </div>
            <h2 className="text-xl font-bold text-[#061907]">Add reminder</h2>
          </div>
          <form onSubmit={create} className="mt-5 space-y-4">
            <Field label="Title" value={form.title} onChange={(value) => setForm((current) => ({ ...current, title: value }))} required />
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Type</span>
              <select value={form.reminder_type} onChange={(event) => setForm((current) => ({ ...current, reminder_type: event.target.value }))} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm">
                <option value="care">Care</option>
                <option value="medication">Medication</option>
                <option value="wound_photo">Wound Photo</option>
                <option value="dressing">Dressing</option>
              </select>
            </label>
            <Field label="Time" type="time" value={form.schedule_time} onChange={(value) => setForm((current) => ({ ...current, schedule_time: value }))} />
            <label className="block">
              <span className="text-sm font-semibold text-[#4d574b]">Notes</span>
              <textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} rows="4" className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" />
            </label>
            {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
            <button className="w-full rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white">Create Reminder</button>
          </form>
        </section>
      </div>
    </AppShell>
  );
}

function Field({ label, value, onChange, type = "text", required = false }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-[#4d574b]">{label}</span>
      <input required={required} type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm" />
    </label>
  );
}
