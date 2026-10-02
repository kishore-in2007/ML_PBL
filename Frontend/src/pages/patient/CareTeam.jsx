import React, { useEffect, useState } from "react";
import { CalendarDays, FileText, Phone, Send, ShieldAlert, Stethoscope, Plus, CheckCircle, Video, UserCheck } from "lucide-react";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function CareTeam() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Fix Consultation Modal state
  const [showModal, setShowModal] = useState(false);
  const [availableDoctors, setAvailableDoctors] = useState([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState("");
  const [appointmentType, setAppointmentType] = useState("video");
  const [scheduledStart, setScheduledStart] = useState("");
  const [reason, setReason] = useState("");
  const [booking, setBooking] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get("/patients/me/care-team")
      .then((response) => setOverview(response.data))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load care team."))
      .finally(() => setLoading(false));

    api
      .get("/patients/doctors")
      .then((res) => {
        setAvailableDoctors(res.data);
        if (res.data.length > 0) {
          setSelectedDoctorId(res.data[0].doctor_id);
        }
      })
      .catch(() => {});
  };

  useEffect(load, []);

  const shareReport = async () => {
    setError("");
    setMessage("");
    try {
      await api.post("/patients/me/share-report", {
        doctor_id: overview?.primary_doctor?.doctor_id,
        title: "Recovery Progress Report",
      });
      setMessage("Recovery report shared with your care team.");
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to share report.");
    }
  };

  const handleBookConsultation = async (e) => {
    e.preventDefault();
    if (!scheduledStart) {
      setError("Please select a date and time for the consultation.");
      return;
    }
    setBooking(true);
    setError("");
    try {
      const startDate = new Date(scheduledStart);
      const endDate = new Date(startDate.getTime() + 30 * 60000); // 30 mins
      await api.post("/patients/me/appointments", {
        doctor_id: selectedDoctorId || overview?.primary_doctor?.doctor_id,
        scheduled_start: startDate.toISOString(),
        scheduled_end: endDate.toISOString(),
        appointment_type: appointmentType,
        reason: reason || "Wound recovery checkup and clinical review",
      });
      setMessage("Consultation fixed successfully with your doctor!");
      setShowModal(false);
      setReason("");
      setScheduledStart("");
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fix consultation.");
    } finally {
      setBooking(false);
    }
  };

  const primary = overview?.primary_doctor;
  const nextAppointment = overview?.upcoming_appointments?.[0];

  return (
    <AppShell role="patient" title="Care Team & Doctor Fixation">
      {loading && <div className="rounded-xl bg-white p-6 shadow-sm">Loading care team...</div>}
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 text-sm mb-4">{error}</div>}
      {message && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 text-sm mb-4 flex items-center gap-2"><CheckCircle size={18} /> {message}</div>}

      {!loading && overview && (
        <div className="space-y-6">
          <section className="rounded-2xl border border-red-100 bg-red-50 p-5 shadow-sm">
            <div className="flex gap-4">
              <ShieldAlert className="mt-1 text-red-700 flex-shrink-0" size={24} />
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-red-800">Emergency & Clinical Guidance</p>
                <p className="mt-1 text-sm text-red-900">{overview.emergency_guidance}</p>
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            {/* Primary Doctor Card */}
            <div className="rounded-2xl border border-[#e4dfd7] bg-white p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between border-b border-[#e4dfd7] pb-4">
                  <div className="flex items-start gap-4">
                    <div className="rounded-2xl bg-emerald-50 p-4 text-emerald-900 border border-emerald-100">
                      <Stethoscope size={32} />
                    </div>
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">Assigned Clinician</span>
                      <h2 className="mt-0.5 text-2xl font-bold text-[#061907]">{primary?.name || "Dr. Vasanthabalan B"}</h2>
                      <p className="text-sm font-semibold text-[#4d574b]">{primary?.specialization || "Post-Surgical Wound Specialist"}</p>
                      <p className="text-xs text-[#667064]">{primary?.hospital_name || "Vithara Clinical Recovery Center"}</p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                    <UserCheck size={14} /> Active
                  </span>
                </div>

                <div className="mt-5 space-y-2 text-sm text-[#4d574b]">
                  <p><b className="text-[#061907]">Direct Contact:</b> {primary?.phone_number || "+91-9876543210"}</p>
                  <p><b className="text-[#061907]">Clinical Focus:</b> {primary?.bio || "Chief Surgeon & Regenerative Wound Healing Specialist"}</p>
                </div>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <button
                  onClick={() => setShowModal(true)}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#061907] px-4 py-3 text-sm font-bold text-white shadow hover:bg-emerald-950 transition-all"
                >
                  <CalendarDays size={18} />
                  Fix Consultation
                </button>
                <button
                  onClick={shareReport}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#061907] px-4 py-3 text-sm font-bold text-[#061907] hover:bg-[#f8f4ee] transition-all"
                >
                  <Send size={18} />
                  Share Recovery Report
                </button>
              </div>
            </div>

            {/* Upcoming Fixed Consultations */}
            <div className="rounded-2xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between border-b border-[#e4dfd7] pb-3 mb-4">
                <h3 className="text-lg font-bold text-[#061907]">Fixed Consultations</h3>
                <button
                  onClick={() => setShowModal(true)}
                  className="inline-flex items-center gap-1 text-xs font-bold text-emerald-800 hover:underline"
                >
                  <Plus size={14} /> Book New
                </button>
              </div>

              {overview.upcoming_appointments && overview.upcoming_appointments.length > 0 ? (
                <div className="space-y-3">
                  {overview.upcoming_appointments.map((apt) => (
                    <div key={apt.id} className="rounded-xl border border-[#e4dfd7] bg-[#faf8f5] p-4">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-[#061907]">{formatDateTime(apt.scheduled_start)}</span>
                        <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800 uppercase">
                          {apt.status}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-[#667064]">
                        Type: <b className="capitalize text-[#061907]">{apt.appointment_type}</b>
                      </p>
                      <p className="mt-1 text-xs text-[#4d574b]">{apt.reason || "Scheduled follow-up"}</p>
                      {apt.meeting_url && (
                        <a
                          href={apt.meeting_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-emerald-800 px-3.5 py-1.5 text-xs font-bold text-white shadow hover:bg-emerald-900"
                        >
                          <Video size={14} /> Open Video Room
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No Upcoming Consultations"
                  message="Use the button below to fix an appointment with your doctor."
                />
              )}
            </div>
          </section>

          {/* Modal for Doctor Fixation */}
          {showModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
              <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-[#e4dfd7]">
                <h3 className="text-xl font-bold text-[#061907]">Fix Doctor Consultation</h3>
                <p className="text-xs text-[#667064] mt-1">Schedule a video call or in-person review with your care team.</p>

                <form onSubmit={handleBookConsultation} className="mt-5 space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase text-[#4d574b] mb-1">Select Doctor</label>
                    <select
                      value={selectedDoctorId}
                      onChange={(e) => setSelectedDoctorId(e.target.value)}
                      className="w-full rounded-xl border border-[#cbdcc7] p-2.5 text-sm focus:outline-none"
                    >
                      {availableDoctors.length > 0 ? (
                        availableDoctors.map((doc) => (
                          <option key={doc.doctor_id} value={doc.doctor_id}>
                            {doc.name || doc.email} - {doc.specialization || "Specialist"}
                          </option>
                        ))
                      ) : (
                        <option value={overview?.primary_doctor?.doctor_id}>
                          {primary?.name || "Dr. Vasanthabalan B (Primary Specialist)"}
                        </option>
                      )}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase text-[#4d574b] mb-1">Consultation Type</label>
                    <select
                      value={appointmentType}
                      onChange={(e) => setAppointmentType(e.target.value)}
                      className="w-full rounded-xl border border-[#cbdcc7] p-2.5 text-sm focus:outline-none"
                    >
                      <option value="video">Live Video Consultation</option>
                      <option value="in_person">In-Person Clinical Visit</option>
                      <option value="emergency">Urgent Priority Review</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase text-[#4d574b] mb-1">Consultation Date & Time</label>
                    <input
                      type="datetime-local"
                      required
                      value={scheduledStart}
                      onChange={(e) => setScheduledStart(e.target.value)}
                      className="w-full rounded-xl border border-[#cbdcc7] p-2.5 text-sm focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase text-[#4d574b] mb-1">Reason / Symptoms for Review</label>
                    <textarea
                      rows={2}
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="e.g., Sutures check, wound area progression review..."
                      className="w-full rounded-xl border border-[#cbdcc7] p-2.5 text-sm focus:outline-none"
                    />
                  </div>

                  <div className="flex gap-3 pt-3">
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="flex-1 rounded-xl border border-[#cbdcc7] py-2.5 text-xs font-bold text-[#4d574b] hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={booking}
                      className="flex-1 rounded-xl bg-[#061907] py-2.5 text-xs font-bold text-white hover:bg-emerald-950 shadow"
                    >
                      {booking ? "Confirming..." : "Confirm & Fix Date"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
