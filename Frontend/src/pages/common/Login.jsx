import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import api, { getBaseUrl } from "../../api/api";

export default function Login({
  allowedRoles = ["patient", "doctor", "nurse", "admin"],
  heading = "Vithara Recovery Monitor",
  subheading = "Your recovery, monitored with care",
  registerPath = "/register",
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showConfig, setShowConfig] = useState(false);
  const [serverUrl, setServerUrl] = useState(getBaseUrl());
  const [pingStatus, setPingStatus] = useState(null); // 'checking', 'success', 'error'
  const [pingMsg, setPingMsg] = useState("");
  const navigate = useNavigate();

  const handlePing = async (urlToTest) => {
    const target = (urlToTest || serverUrl || "").trim().replace(/\/+$/, "");
    if (!target) return;
    setPingStatus("checking");
    setPingMsg("Connecting to server...");
    try {
      const res = await axios.get(`${target}/health`, { timeout: 4000 });
      setPingStatus("success");
      setPingMsg(`Connected! Status ${res.status} (${res.data?.status || "online"})`);
    } catch (err) {
      setPingStatus("error");
      setPingMsg(`Failed to connect: ${err.message || "Network unreachable"}`);
    }
  };

  const handleSaveServer = () => {
    const clean = (serverUrl || "").trim().replace(/\/+$/, "");
    if (clean) {
      localStorage.setItem("vithara_api_url", clean);
      setServerUrl(clean);
      setShowConfig(false);
    }
  };

  const handleResetServer = (defaultVal) => {
    setServerUrl(defaultVal);
    localStorage.setItem("vithara_api_url", defaultVal);
    handlePing(defaultVal);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const response = await api.post("/auth/login", { email, password });
      const { access_token, user } = response.data;

      if (!allowedRoles.includes(user.role)) {
        setError("This account does not have access to this portal.");
        return;
      }

      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(user));

      if (user.role === "patient") {
        navigate("/patient/dashboard");
      } else if (["doctor", "nurse", "admin"].includes(user.role)) {
        navigate("/doctor/dashboard");
      } else {
        setError("Invalid user role assigned. Please contact support.");
      }
    } catch (err) {
      console.error(err);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError(`Unable to connect to authentication server at ${getBaseUrl()}. Tap "Server Settings" below to configure your backend API address.`);
      }
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-gradient-to-br from-[#eef6f0] via-[#f7faf8] to-[#e8f1eb] relative overflow-x-hidden">
      {/* Background Ambient Glows */}
      <div className="fixed -top-24 -right-24 w-96 h-96 bg-emerald-200/50 rounded-full blur-3xl pointer-events-none z-0"></div>
      <div className="fixed -bottom-24 -left-24 w-96 h-96 bg-teal-200/40 rounded-full blur-3xl pointer-events-none z-0"></div>

      <main className="relative z-10 w-full max-w-5xl grid md:grid-cols-12 bg-white rounded-3xl overflow-hidden shadow-2xl border border-emerald-950/10 my-auto">
        {/* Left Clinical Showcase Panel (5 cols on md+) */}
        <div className="hidden md:flex md:col-span-5 flex-col justify-between bg-gradient-to-b from-[#061907] via-[#092b10] to-[#04160b] p-8 lg:p-10 text-white relative overflow-hidden">
          {/* Subtle Ambient Background Gradients */}
          <div className="absolute -top-16 -left-16 w-56 h-56 bg-emerald-500/20 rounded-full blur-2xl pointer-events-none"></div>
          <div className="absolute bottom-0 right-0 w-64 h-64 bg-emerald-400/10 rounded-full blur-3xl pointer-events-none"></div>

          {/* Top Brand Identity */}
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-11 h-11 bg-emerald-500/20 border border-emerald-400/30 rounded-2xl flex items-center justify-center shadow-inner">
                <span className="material-symbols-outlined text-emerald-400 text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  medical_services
                </span>
              </div>
              <div>
                <span className="text-xl font-bold tracking-tight text-white block">Vithara</span>
                <span className="text-[11px] text-emerald-300/80 font-medium tracking-wide uppercase">Clinical Recovery AI</span>
              </div>
            </div>

            <h2 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug mb-3">
              Patient-Centric Recovery & Clinical Triage
            </h2>
            <p className="text-xs lg:text-sm text-emerald-100/70 leading-relaxed">
              Automated postoperative wound assessment, computer vision healing trajectory analysis, and proactive clinical escalation.
            </p>
          </div>

          {/* Feature Highlights Grid */}
          <div className="relative z-10 space-y-3.5 my-8">
            <div className="flex items-center gap-3.5 p-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm transition-all hover:bg-white/10">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-300 shrink-0">
                <span className="material-symbols-outlined text-lg">healing</span>
              </div>
              <div className="text-left">
                <h4 className="text-xs font-bold text-white">AI Wound Segmentation</h4>
                <p className="text-[11px] text-emerald-200/70">Tissue area quantification & infection risk classification</p>
              </div>
            </div>

            <div className="flex items-center gap-3.5 p-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm transition-all hover:bg-white/10">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-300 shrink-0">
                <span className="material-symbols-outlined text-lg">analytics</span>
              </div>
              <div className="text-left">
                <h4 className="text-xs font-bold text-white">Longitudinal Tracking</h4>
                <p className="text-[11px] text-emerald-200/70">Healing progress comparison against initial postoperative baseline</p>
              </div>
            </div>

            <div className="flex items-center gap-3.5 p-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm transition-all hover:bg-white/10">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-300 shrink-0">
                <span className="material-symbols-outlined text-lg">mic</span>
              </div>
              <div className="text-left">
                <h4 className="text-xs font-bold text-white">Voice Symptom Check-ins</h4>
                <p className="text-[11px] text-emerald-200/70">Hands-free recovery logging powered by speech AI</p>
              </div>
            </div>
          </div>

          {/* Bottom Security / Status Footer */}
          <div className="relative z-10 pt-4 border-t border-white/10 flex items-center justify-between text-[11px] text-emerald-200/80">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Clinical Engine Active
            </span>
            <span className="text-emerald-300/60 font-mono text-[10px]">HIPAA Aligned</span>
          </div>
        </div>

        {/* Right Form Panel (7 cols on md+) */}
        <div className="p-6 sm:p-10 lg:p-12 md:col-span-7 flex flex-col justify-center bg-white">
          <header className="mb-6 text-left">
            <div className="flex items-center gap-2 mb-3 md:hidden">
              <div className="w-9 h-9 bg-[#061907] flex items-center justify-center rounded-xl">
                <span className="material-symbols-outlined text-white text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                  medical_services
                </span>
              </div>
              <span className="font-bold text-xl text-[#061907] tracking-tight">Vithara</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#061907] tracking-tight mb-1.5">{heading}</h1>
            <p className="text-xs sm:text-sm text-[#546051]">{subheading}</p>
          </header>

          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3.5 bg-red-50 text-red-900 border border-red-200 rounded-2xl text-xs space-y-2 animate-fade-in">
                <div className="flex items-start gap-2">
                  <span className="material-symbols-outlined text-red-600 text-base shrink-0 mt-0.5">error</span>
                  <div className="flex-1 leading-relaxed">
                    <span>{error}</span>
                  </div>
                </div>
                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setShowConfig(true);
                      handlePing(serverUrl);
                    }}
                    className="inline-flex items-center gap-1 font-bold text-red-800 hover:text-red-950 underline text-[11px]"
                  >
                    <span>⚙️ Configure Server URL</span>
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-[#3b4739] block" htmlFor="email">
                Email Address
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400 group-focus-within:text-emerald-700">
                  <span className="material-symbols-outlined text-lg">mail</span>
                </div>
                <input
                  className="block w-full h-12 pl-10 pr-4 bg-[#f8fbf8] border border-[#d2ddd0] rounded-xl text-sm text-[#061907] focus:ring-2 focus:ring-emerald-600 focus:border-transparent focus:bg-white transition-all outline-none"
                  id="email"
                  name="email"
                  placeholder="patient@vithara.com"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-[#3b4739]" htmlFor="password">
                  Password
                </label>
                <button type="button" onClick={() => alert("Please use the 1-Click Demo buttons below or contact your clinic administrator.")} className="text-xs font-semibold text-emerald-800 hover:underline">
                  Forgot?
                </button>
              </div>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400 group-focus-within:text-emerald-700">
                  <span className="material-symbols-outlined text-lg">lock</span>
                </div>
                <input
                  className="block w-full h-12 pl-10 pr-4 bg-[#f8fbf8] border border-[#d2ddd0] rounded-xl text-sm text-[#061907] focus:ring-2 focus:ring-emerald-600 focus:border-transparent focus:bg-white transition-all outline-none"
                  id="password"
                  name="password"
                  placeholder="••••••••"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                className="w-full h-12 bg-[#061907] hover:bg-emerald-950 text-white font-bold text-sm rounded-xl transition-all transform active:scale-[0.99] shadow-md flex items-center justify-center gap-2 group cursor-pointer"
                type="submit"
              >
                <span>Login</span>
                <span className="material-symbols-outlined text-base group-hover:translate-x-1 transition-transform">
                  arrow_forward
                </span>
              </button>
            </div>
          </form>

          {/* Quick 1-Click Demos */}
          <div className="mt-5 pt-4 border-t border-[#edf2ec]">
            <div className="text-[11px] font-bold text-[#627060] uppercase tracking-wider mb-2 text-center">
              Quick Test Accounts
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setEmail("patient@vithara.com");
                  setPassword("Password123!");
                }}
                className="inline-flex h-10 items-center justify-center rounded-xl border border-emerald-300 bg-emerald-50 px-2 text-xs font-bold text-emerald-900 hover:bg-emerald-100 transition-all cursor-pointer"
              >
                ⚡ 1-Click Patient
              </button>
              <button
                type="button"
                onClick={() => {
                  setEmail("doctor@vithara.com");
                  setPassword("Password123!");
                }}
                className="inline-flex h-10 items-center justify-center rounded-xl border border-blue-300 bg-blue-50 px-2 text-xs font-bold text-blue-900 hover:bg-blue-100 transition-all cursor-pointer"
              >
                ⚡ 1-Click Doctor
              </button>
            </div>

            {/* Portal Switcher */}
            <div className="grid grid-cols-2 gap-2 mt-2">
              <Link
                to="/patient/login"
                className="inline-flex h-9 items-center justify-center rounded-xl border border-[#d2ddd0] bg-white px-2 text-xs font-semibold text-[#061907] hover:bg-[#f3f7f2] transition-all text-center"
              >
                Patient Portal
              </Link>
              <Link
                to="/doctor/login"
                className="inline-flex h-9 items-center justify-center rounded-xl border border-[#d2ddd0] bg-white px-2 text-xs font-semibold text-[#061907] hover:bg-[#f3f7f2] transition-all text-center"
              >
                Doctor Portal
              </Link>
            </div>

            {/* Create Account & Server Info */}
            <div className="mt-4 flex flex-col items-center gap-2">
              <div className="text-xs text-[#546051]">
                New to Vithara?{" "}
                <Link to={registerPath} className="font-bold text-emerald-900 hover:underline">
                  Create an account
                </Link>
              </div>

              {/* Server Connection Status Button */}
              <button
                type="button"
                onClick={() => {
                  setShowConfig(true);
                  handlePing(serverUrl);
                }}
                className="mt-1 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#f2f7f2] hover:bg-[#e4ede4] border border-[#d2ddd0] text-[11px] text-[#475444] transition-all"
              >
                <span className="material-symbols-outlined text-sm text-emerald-700">dns</span>
                <span>Server: <span className="font-mono font-medium">{serverUrl}</span></span>
                <span className="font-bold text-emerald-800 underline ml-0.5">Edit</span>
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Server Config Modal */}
      {showConfig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-[#e4dfd7]">
            <div className="flex items-center justify-between pb-3 border-b border-[#e4dfd7]">
              <div>
                <h3 className="text-base font-bold text-[#061907]">Backend Server Connection</h3>
                <p className="text-xs text-[#667064]">Configure API URL for cloud hosting or local testing</p>
              </div>
              <button
                type="button"
                onClick={() => setShowConfig(false)}
                className="rounded-lg p-1 text-[#667064] hover:bg-gray-100 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#061907] mb-1">Backend API Base URL</label>
                <input
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="https://vithara-backend.onrender.com"
                  className="w-full rounded-xl border border-[#cbdcc7] px-3.5 py-2.5 text-sm font-mono text-[#061907] focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
                <p className="mt-1 text-[11px] text-[#667064]">
                  Enter your hosted backend URL (e.g., Render, Railway, or ngrok tunnel)
                </p>
              </div>

              {/* Quick Presets */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-bold text-[#667064] uppercase tracking-wider">Quick Presets:</span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleResetServer("http://127.0.0.1:8000")}
                    className="rounded-lg border border-gray-300 bg-gray-50 px-2.5 py-1.5 text-left text-xs font-semibold text-gray-800 hover:bg-gray-100 transition-all cursor-pointer"
                  >
                    💻 Localhost
                    <div className="text-[10px] font-mono text-gray-600 truncate">127.0.0.1:8000</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleResetServer("http://10.206.162.226:8000")}
                    className="rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-left text-xs font-semibold text-emerald-900 hover:bg-emerald-100 transition-all cursor-pointer"
                  >
                    📡 Wi-Fi IP
                    <div className="text-[10px] font-mono text-emerald-700 truncate">10.206.162.226:8000</div>
                  </button>
                </div>
              </div>

              {/* Ping Status */}
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-700">Connection Test:</span>
                  <button
                    type="button"
                    onClick={() => handlePing(serverUrl)}
                    className="rounded-lg bg-gray-200 px-2.5 py-1 text-[11px] font-bold text-gray-800 hover:bg-gray-300 transition-all cursor-pointer"
                  >
                    {pingStatus === "checking" ? "Testing..." : "Ping Now"}
                  </button>
                </div>
                {pingMsg && (
                  <p className={`mt-2 font-mono text-[11px] ${
                    pingStatus === "success" ? "text-emerald-700 font-bold" : pingStatus === "error" ? "text-red-600" : "text-gray-600"
                  }`}>
                    {pingStatus === "success" ? "✓ " : pingStatus === "error" ? "✗ " : "⏳ "}{pingMsg}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-[#e4dfd7] pt-4">
              <button
                type="button"
                onClick={() => setShowConfig(false)}
                className="rounded-xl border border-gray-300 px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-100 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveServer}
                className="rounded-xl bg-[#061907] px-5 py-2 text-xs font-bold text-white shadow hover:bg-emerald-950 cursor-pointer"
              >
                Save & Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
