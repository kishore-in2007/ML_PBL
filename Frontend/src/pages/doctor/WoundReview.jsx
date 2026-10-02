import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../../api/api";
import { formatDateTime, mediaUrl, number } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function WoundReview() {
  const [searchParams] = useSearchParams();
  const imageId = searchParams.get("image_id");
  const patientId = searchParams.get("patient_id");
  const [image, setImage] = useState(null);
  const [patients, setPatients] = useState([]);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    if (imageId) {
      api
        .get(`/doctor/wound-images/${imageId}`)
        .then((response) => setImage(response.data))
        .catch((err) => setError(err.response?.data?.detail || "Unable to load wound image."))
        .finally(() => setLoading(false));
    } else {
      api
        .get("/doctor/patients")
        .then((response) => setPatients(response.data || []))
        .finally(() => setLoading(false));
    }
  }, [imageId]);

  const saveNote = async () => {
    setError("");
    setMessage("");
    if (!note.trim()) {
      setError("Enter a clinical note before saving.");
      return;
    }
    try {
      await api.post("/doctor/clinical-notes", {
        patient_id: image?.patient_id || patientId,
        image_id: image?.image_id || imageId,
        note,
      });
      setMessage("Clinical note saved.");
      setNote("");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to save clinical note.");
    }
  };

  return (
    <AppShell role="doctor" title="Wound Image Review">
      {loading && <div className="rounded-xl bg-white p-6 shadow-sm">Loading wound review...</div>}

      {!loading && !imageId && (
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-[#061907]">Select a patient image to review</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {patients.length ? (
              patients.map((item) => (
                <article key={item.patient.id} className="rounded-xl border border-[#e4dfd7] p-4">
                  <img src={mediaUrl(item.latest_image_url)} alt="Latest wound" className="h-48 w-full rounded-lg bg-[#f8f4ee] object-cover" />
                  <p className="mt-3 font-bold text-[#061907]">Patient {item.patient.id}</p>
                  <p className="text-sm text-[#667064]">{item.latest_risk_class || "No risk class"} • {item.healing_trend || "No trend"}</p>
                  {item.latest_image_id ? (
                    <Link to={`/doctor/wound-review?image_id=${item.latest_image_id}&patient_id=${item.patient.id}`} className="mt-4 inline-flex w-full justify-center rounded-lg bg-[#061907] px-4 py-2 text-sm font-bold text-white">
                      Open Wound Details
                    </Link>
                  ) : (
                    <p className="mt-4 text-sm text-[#667064]">No uploaded wound image.</p>
                  )}
                </article>
              ))
            ) : (
              <EmptyState title="No patient images" message="Daily wound uploads from assigned patients will appear here." />
            )}
          </div>
        </section>
      )}

      {!loading && imageId && image && (
        <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
          <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-[#061907]">Segmentation and original image</h2>
            <img src={mediaUrl(image.mask_overlay_url || image.image_url)} alt="Wound segmentation" className="mt-4 h-[460px] w-full rounded-lg bg-[#f8f4ee] object-contain" />
            {image.mask_overlay_url && (
              <a href={mediaUrl(image.image_url)} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-sm font-bold text-[#061907] hover:underline">
                View original uploaded image
              </a>
            )}
          </section>

          <section className="space-y-6">
            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-[#061907]">Model summary</h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Metric label="Patient" value={image.patient_id} />
                <Metric label="Uploaded" value={formatDateTime(image.uploaded_at)} />
                <Metric label="Risk" value={image.risk_class || "--"} />
                <Metric label="Confidence" value={image.confidence ? `${(image.confidence * 100).toFixed(1)}%` : "--"} />
                <Metric label="Human Review" value={image.needs_human_review ? "Required" : "Not required"} />
                <Metric label="Area" value={number(image.wound_area_cm2, " cm²")} />
                <Metric label="Change vs Previous" value={image.percent_change_from_previous !== null && image.percent_change_from_previous !== undefined ? `${image.percent_change_from_previous.toFixed(1)}%` : "--"} />
                <Metric label="Segmentation" value={image.segmentation_model_used || "--"} />
              </div>
            </div>

            <div className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-[#061907]">Doctor note</h3>
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows="6"
                className="mt-3 w-full rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] p-3 text-sm"
                placeholder="Summarize wound status, dressing advice, follow-up, or emergency action."
              />
              {message && <div className="mt-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
              {error && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
              <button onClick={saveNote} className="mt-4 rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white">
                Save Clinical Note
              </button>
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
