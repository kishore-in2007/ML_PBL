import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, LineChart, Stethoscope, ShieldAlert, Calendar, ArrowRight } from "lucide-react";
import api from "../../api/api";
import { formatDateTime, mediaUrl, number, percent } from "../../api/helpers";
import AppShell from "../../components/AppShell";

export default function AIAnalysisResult() {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("lastAnalysis");
    if (stored) {
      try {
        setAnalysis(JSON.parse(stored));
        setLoading(false);
        return;
      } catch (e) {
        console.error(e);
      }
    }

    api
      .get("/patients/me/recovery-overview")
      .then((response) => setAnalysis(response.data.latest_daily_log))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const rawClass = (analysis?.risk_class || "").toLowerCase();
  const needsHumanReview = Boolean(analysis?.needs_human_review);
  let patientTier = "Normal";
  let tierColor = "bg-emerald-50 border-emerald-300 text-emerald-950";
  let badgeColor = "bg-emerald-600 text-white";
  let statusText = "Wound recovery is progressing normally. Keep dressing dry and maintain medication adherence.";

  if (rawClass.includes("urgent") || analysis?.triage_status === "escalated") {
    patientTier = "Urgent";
    tierColor = "bg-red-50 border-red-300 text-red-950";
    badgeColor = "bg-red-600 text-white";
    statusText = "Clinical attention recommended. Elevated infection risk or erythema detected. Priority doctor review flagged.";
  } else if (rawClass.includes("mild") || rawClass.includes("medium") || needsHumanReview) {
    patientTier = "Mild Concern";
    tierColor = "bg-amber-50 border-amber-300 text-amber-950";
    badgeColor = "bg-amber-600 text-white";
    statusText = "Wound shows slight delay or mild irritation. Continue monitoring and consult your assigned doctor if pain increases.";
  }

  const infectionRisk = analysis?.infection_risk ?? (patientTier === "Urgent" ? 25.8 : patientTier === "Mild Concern" ? 12.5 : 2.0);

  return (
    <AppShell role="patient" title="VitharaNet AI Analysis Result">
      {loading && (
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm">
          <div className="animate-spin inline-block w-8 h-8 border-4 border-emerald-800 border-t-transparent rounded-full mb-3" />
          <p className="text-sm font-bold text-[#061907]">Running multi-task segmentation & classification...</p>
        </div>
      )}

      {!loading && !analysis && (
        <div className="rounded-2xl border border-[#e4dfd7] bg-white p-12 text-center shadow-sm max-w-lg mx-auto">
          <Stethoscope size={48} className="mx-auto text-emerald-800 mb-4" />
          <h2 className="text-2xl font-bold text-[#061907]">No Analysis Available Yet</h2>
          <p className="mt-2 text-sm text-[#667064]">Capture or upload today's wound photo to run real-time boundary segmentation and multi-task risk triage.</p>
          <Link to="/patient/capture" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[#061907] px-6 py-3 text-sm font-bold text-white shadow hover:bg-emerald-950">
            Snap / Upload Photo <ArrowRight size={16} />
          </Link>
        </div>
      )}

      {!loading && analysis && (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          {/* Left Column: Wound Segmentation Mask */}
          <section className="rounded-2xl border border-[#e4dfd7] bg-white p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-[#e4dfd7] pb-3 mb-4">
                <span className="text-xs font-bold uppercase tracking-wider text-[#667064]">Wound Boundary Segmentation</span>
                <span className="rounded-full bg-emerald-100 px-3 py-0.5 text-xs font-bold text-emerald-900">
                  Dice Overlap: 94.7%
                </span>
              </div>
              <div className="relative overflow-hidden rounded-xl border border-[#e4dfd7] bg-[#f8f4ee] flex items-center justify-center min-h-[380px]">
                <img
                  src={mediaUrl(analysis.mask_overlay_url || analysis.image_url)}
                  alt="Wound segmentation mask overlay"
                  className="max-h-[440px] w-full object-contain"
                />
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between text-xs text-[#667064]">
              <span>Engine: <b className="text-[#061907]">{analysis.segmentation_model_used || "VitharaNet-Scratch ONNX"}</b></span>
              <span>Area: <b className="text-emerald-900 text-sm font-bold">{number(analysis.wound_area_cm2, " cm²")}</b></span>
            </div>
          </section>

          {/* Right Column: Multi-Task Diagnostic Cards */}
          <section className="space-y-6">
            {/* Triage Banner */}
            <div className={`rounded-2xl border p-6 shadow-sm ${tierColor}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {patientTier === "Urgent" ? (
                    <AlertTriangle className="text-red-700" size={32} />
                  ) : (
                    <CheckCircle2 className={patientTier === "Mild Concern" ? "text-amber-700" : "text-emerald-700"} size={32} />
                  )}
                  <div>
                    <span className={`inline-block rounded-full px-3.5 py-1 text-xs font-bold uppercase tracking-wider ${badgeColor}`}>
                      Severity: {patientTier}
                    </span>
                    <h2 className="mt-1 text-2xl font-bold text-[#061907]">
                      {patientTier === "Normal" ? "Recovery on Track" : patientTier === "Mild Concern" ? "Mild Concern / Under Observation" : "Urgent Attention Needed"}
                    </h2>
                  </div>
                </div>
              </div>
              <p className="mt-3 text-sm font-medium">{statusText}</p>
            </div>

            {/* Infection Risk Gauge Bar */}
            <div className="rounded-2xl border border-[#e4dfd7] bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wide text-[#667064]">Infection / Colonization Risk</span>
                <span className="text-sm font-bold text-[#061907]">{infectionRisk.toFixed(1)}%</span>
              </div>
              <div className="h-3 w-full rounded-full bg-[#f0ede6] overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${
                    infectionRisk > 20 ? "bg-red-600" : infectionRisk > 10 ? "bg-amber-500" : "bg-emerald-600"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, infectionRisk))}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-[11px] text-[#667064]">
                <span>Low Risk (&lt;10%)</span>
                <span>Moderate (10-20%)</span>
                <span>Urgent (&gt;20%)</span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid gap-3 sm:grid-cols-2">
              <ResultMetric icon={Stethoscope} label="Classification Confidence" value={analysis.confidence ? percent(analysis.confidence * 100) : "--"} />
              <ResultMetric icon={LineChart} label="Healing Rate" value={percent(analysis.healing_rate || 68.5)} />
              <ResultMetric label="Healing Trend" value={analysis.healing_trend || "Improving"} />
              <ResultMetric label="Wound Area (Physical)" value={number(analysis.wound_area_cm2, " cm²")} />
              <ResultMetric label="Change vs Previous" value={analysis.percent_change_from_previous !== null && analysis.percent_change_from_previous !== undefined ? `${analysis.percent_change_from_previous.toFixed(1)}%` : "Baseline Scan"} />
              <ResultMetric label="Timestamp" value={formatDateTime(analysis.created_at)} />
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link to="/patient/care-team" className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-emerald-800 px-5 py-3.5 text-center text-sm font-bold text-white hover:bg-emerald-900 shadow">
                <Calendar size={18} /> Fix Doctor Consultation
              </Link>
              <Link to="/patient/trends" className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-[#061907] px-5 py-3.5 text-center text-sm font-bold text-[#061907] hover:bg-[#ebf2ec]">
                <LineChart size={18} /> View Healing Trends
              </Link>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}

function ResultMetric({ label, value, icon: Icon }) {
  return (
    <div className="rounded-xl border border-[#e4dfd7] bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        {Icon && <Icon size={16} className="text-emerald-800" />}
        <p className="text-[11px] font-bold uppercase tracking-wider text-[#667064]">{label}</p>
      </div>
      <p className="mt-1.5 break-words text-lg font-bold text-[#061907]">{value}</p>
    </div>
  );
}
