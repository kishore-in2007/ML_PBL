import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, UploadCloud, RefreshCw, CheckCircle2, AlertCircle, Video, Smartphone } from "lucide-react";
import api from "../../api/api";
import AppShell from "../../components/AppShell";

export default function CaptureWoundPhoto() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("camera"); // 'camera' or 'upload'
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [painLevel, setPainLevel] = useState(2);
  const [fever, setFever] = useState(false);
  const [medicationAdherence, setMedicationAdherence] = useState(true);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Live Camera states
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const startCamera = async () => {
    setCameraError("");
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setCameraActive(true);
    } catch (err) {
      console.error("Camera access error:", err);
      setCameraError("Camera access denied or not available. Please switch to file upload or allow camera permissions.");
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    if (mode === "camera" && !preview) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [mode, preview]);

  const snapPhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) {
        const snapFile = new File([blob], `wound_snap_${Date.now()}.jpg`, { type: "image/jpeg" });
        setFile(snapFile);
        setPreview(URL.createObjectURL(snapFile));
        stopCamera();
      }
    }, "image/jpeg", 0.95);
  };

  const retakePhoto = () => {
    setFile(null);
    setPreview("");
    if (mode === "camera") {
      startCamera();
    }
  };

  const onFileChange = (event) => {
    const selected = event.target.files?.[0];
    if (selected) {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      stopCamera();
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Please capture or choose a wound photo first.");
      return;
    }
    setSubmitting(true);
    setError("");

    const form = new FormData();
    form.append("file", file);
    form.append("pain_level", painLevel);
    form.append("fever", fever);
    form.append("medication_adherence", medicationAdherence);
    form.append("notes", notes);

    try {
      const response = await api.post("/patients/me/daily-wound-photo", form);
      localStorage.setItem("lastAnalysis", JSON.stringify(response.data));
      navigate("/patient/analysis-result");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : `Unable to upload and analyze this image. ${err.message || ""}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell role="patient" title="Capture & Upload Wound Photo">
      <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-2xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
          {/* Dual Mode Switcher */}
          <div className="flex items-center justify-between border-b border-[#e4dfd7] pb-4">
            <div>
              <h2 className="text-xl font-bold text-[#061907]">Wound Photo Input</h2>
              <p className="text-xs text-[#667064]">Choose between live high-resolution camera capture or local device upload.</p>
            </div>
            <div className="flex rounded-xl bg-[#f0ede6] p-1 border border-[#e4dfd7]">
              <button
                type="button"
                onClick={() => {
                  setMode("camera");
                  setFile(null);
                  setPreview("");
                }}
                className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-bold transition-all ${
                  mode === "camera" ? "bg-[#061907] text-white shadow" : "text-[#4d574b] hover:text-[#061907]"
                }`}
              >
                <Video size={15} />
                Live Camera
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("upload");
                  stopCamera();
                }}
                className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-bold transition-all ${
                  mode === "upload" ? "bg-[#061907] text-white shadow" : "text-[#4d574b] hover:text-[#061907]"
                }`}
              >
                <Smartphone size={15} />
                Local Device
              </button>
            </div>
          </div>

          {/* Viewport Area */}
          <div className="mt-5">
            {preview ? (
              <div className="relative overflow-hidden rounded-xl border border-[#cbdcc7] bg-[#061907]/5">
                <img src={preview} alt="Captured wound preview" className="max-h-[460px] w-full object-contain" />
                <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-3 px-4">
                  <button
                    type="button"
                    onClick={retakePhoto}
                    className="flex items-center gap-2 rounded-xl bg-white/95 backdrop-blur px-5 py-2.5 text-xs font-bold text-[#061907] shadow hover:bg-white"
                  >
                    <RefreshCw size={15} />
                    Retake / Choose Another
                  </button>
                </div>
              </div>
            ) : mode === "camera" ? (
              <div className="relative min-h-[380px] overflow-hidden rounded-xl border border-[#061907]/20 bg-black flex flex-col items-center justify-center">
                <video
                  ref={videoRef}
                  className={`h-full max-h-[440px] w-full object-cover ${cameraActive ? "block" : "hidden"}`}
                  playsInline
                  autoPlay
                  muted
                />
                {!cameraActive && (
                  <div className="p-6 text-center text-white">
                    <Camera size={44} className="mx-auto mb-3 text-emerald-400 animate-pulse" />
                    <p className="text-sm font-semibold">{cameraError || "Initializing camera viewfinder..."}</p>
                    <button
                      type="button"
                      onClick={startCamera}
                      className="mt-4 inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-emerald-500"
                    >
                      <RefreshCw size={14} /> Retry Camera
                    </button>
                  </div>
                )}
                {cameraActive && (
                  <div className="absolute bottom-4 left-0 right-0 flex justify-center">
                    <button
                      type="button"
                      onClick={snapPhoto}
                      className="flex items-center gap-2 rounded-2xl bg-white px-6 py-3 text-sm font-bold text-[#061907] shadow-xl hover:scale-105 active:scale-95 transition-all"
                    >
                      <Camera size={18} className="text-emerald-700" />
                      Snap Wound Photo
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <label className="flex min-h-[380px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#cbdcc7] bg-[#f8f4ee] p-6 text-center hover:bg-[#f3efe8] transition-all">
                <UploadCloud size={46} className="text-emerald-700 mb-2" />
                <p className="text-base font-bold text-[#061907]">Select Wound Image from Device</p>
                <p className="mt-1 text-xs text-[#667064]">Click or drag & drop JPG, PNG, or WEBP photos</p>
                <span className="mt-4 rounded-xl bg-[#061907] px-4 py-2 text-xs font-bold text-white shadow">
                  Browse Device Gallery
                </span>
                <input type="file" accept="image/*" className="sr-only" onChange={onFileChange} />
              </label>
            )}
          </div>
        </section>

        {/* Symptoms & Submit Section */}
        <section className="rounded-2xl border border-[#e4dfd7] bg-white p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-[#061907]">Daily Healing Symptoms</h3>
            <p className="text-xs text-[#667064] mt-0.5">Assists VitharaNet multi-task clinical triage.</p>

            <div className="mt-5 space-y-5">
              <label className="block rounded-xl border border-[#e4dfd7] p-4 bg-[#faf8f5]">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold text-[#061907]">Pain Severity:</span>
                  <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    painLevel > 6 ? "bg-red-100 text-red-800" : painLevel > 3 ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
                  }`}>
                    {painLevel} / 10
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={painLevel}
                  onChange={(e) => setPainLevel(parseInt(e.target.value))}
                  className="mt-3 w-full accent-[#061907]"
                />
              </label>

              <label className="flex items-center justify-between rounded-xl border border-[#e4dfd7] p-4 bg-[#faf8f5] cursor-pointer">
                <div>
                  <span className="block font-semibold text-sm text-[#061907]">Fever or Shivering Today</span>
                  <span className="text-xs text-[#667064]">Triggers prioritized infection screening</span>
                </div>
                <input
                  type="checkbox"
                  checked={fever}
                  onChange={(e) => setFever(e.target.checked)}
                  className="h-5 w-5 rounded accent-emerald-800"
                />
              </label>

              <label className="flex items-center justify-between rounded-xl border border-[#e4dfd7] p-4 bg-[#faf8f5] cursor-pointer">
                <div>
                  <span className="block font-semibold text-sm text-[#061907]">Medication Adherence</span>
                  <span className="text-xs text-[#667064]">Antiseptics and antibiotics taken on schedule</span>
                </div>
                <input
                  type="checkbox"
                  checked={medicationAdherence}
                  onChange={(e) => setMedicationAdherence(e.target.checked)}
                  className="h-5 w-5 rounded accent-emerald-800"
                />
              </label>

              <label className="block">
                <span className="block text-xs font-semibold text-[#4d574b] uppercase tracking-wide mb-1">
                  Patient Notes for Doctor
                </span>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Note any discharge, itching, burning, dressing changes..."
                  className="w-full rounded-xl border border-[#cbdcc7] p-3 text-sm focus:border-[#061907] focus:outline-none"
                />
              </label>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#e4dfd7]">
            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 font-medium">
                <AlertCircle size={16} />
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={submitting || !file}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#061907] py-3.5 text-sm font-bold text-white shadow-lg transition-all hover:bg-emerald-950 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <>
                  <RefreshCw className="animate-spin" size={18} />
                  Evaluating with VitharaNet ONNX...
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} />
                  Upload & Run AI Recovery Analysis
                </>
              )}
            </button>
          </div>
        </section>
      </form>
    </AppShell>
  );
}
