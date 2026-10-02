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
        setError(`Unable to connect to authentication server at ${getBaseUrl()}. Tap "Server Settings" below to configure host IP.`);
      }
    }
  };

  return (
    <>
      <div className="fixed -top-20 -right-20 w-96 h-96 bg-surface-mint rounded-full blur-3xl opacity-50 z-0"></div>
      <div className="fixed -bottom-20 -left-20 w-96 h-96 bg-secondary-fixed opacity-20 rounded-full blur-3xl z-0"></div>
      <main className="relative z-10 w-full max-w-[1100px] grid md:grid-cols-2 bg-surface-container-lowest rounded-3xl overflow-hidden soft-shadow">


        <div className="hidden md:flex flex-col justify-center items-center bg-surface-mint p-12 relative overflow-hidden">


          <div className="absolute inset-0 z-0 flex items-center justify-center opacity-40">

            <div className="w-[400px] h-[400px] bg-primary-fixed-dim rounded-full floating-shape blur-xl"></div>
            <div className="absolute w-[300px] h-[300px] bg-tertiary-fixed rounded-full floating-shape blur-xl" style={{ "animationDelay": "-2s" }}></div>

          </div>
          <div className="relative z-10 text-center">

            <div className="mb-8 rounded-2xl overflow-hidden shadow-lg border border-white/40">

              <img className="w-full h-[320px] object-cover" data-alt="A soft and welcoming digital illustration of a serene healthcare environment with organic green shapes and warm lighting. The image features a minimalist wooden desk with a small green plant and soft sunlight streaming through a window, creating a peaceful and nurturing atmosphere. The color palette is composed of light sage, ivory, and soft peach tones to evoke a sense of professional care and stability." src="https://lh3.googleusercontent.com/aida-public/AB6AXuCREUiA6puXWrh0bkf48oWxRGSq9wo7zGvSXjYhyKGmLyYhTPhMnFf7Nv1FVlCvfRfsBSagvz5HG0TE_rKQROHv7lFl_hxeCkoDIxpfTx_e2fOgraAcsCHvYujxPKEzdd7yKJs9MECDhQV5uvh8OAbUmwUYJpL9T1pN1WJ_pAGDvQL0fna4AE7xafoFCBmTgeWYoecQm-8kRdxZ7yjnsUqUoc4xH_PTOaGLi5XRcqOzaQxopjeOYeC9AA" />

            </div>
            <h2 className="font-headline-lg text-headline-lg text-primary mb-4">Patient-Centric Care</h2>
            <p className="font-body-lg text-body-lg text-on-surface-variant max-w-sm mx-auto">
                    A warm, hospitality-inspired environment designed to support your journey back to full health.
                </p>

          </div>

        </div>

        <div className="p-8 md:p-16 flex flex-col justify-center bg-surface-container-lowest">

          <header className="mb-10 text-center md:text-left">

            <div className="flex items-center justify-center md:justify-start gap-2 mb-6">

              <div className="w-10 h-10 bg-primary flex items-center justify-center rounded-xl">

                <span className="material-symbols-outlined text-white" style={{ "fontVariationSettings": "'FILL' 1" }}>medical_services</span>

              </div>
              <span className="font-headline-md text-headline-md font-bold text-primary tracking-tight">Vithara</span>

            </div>
            <h1 className="font-headline-lg-mobile text-headline-lg-mobile md:font-headline-lg md:text-headline-lg text-text-charcoal mb-2">{heading}</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">{subheading}</p>

          </header>
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="p-4 bg-red-50 text-red-800 border border-red-200 rounded-xl text-sm font-body-md animate-fade-in flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">error</span>
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">

              <label className="font-label-md text-label-md text-on-surface-variant ml-1" htmlFor="email">Email Address</label>
              <div className="relative group input-focus-glow rounded-xl transition-all">

                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">

                  <span className="material-symbols-outlined text-outline">mail</span>

                </div>
                <input className="block w-full h-14 pl-12 pr-4 bg-surface-container-low border-none rounded-xl font-body-md text-body-md focus:ring-2 focus:ring-primary-fixed-dim transition-all text-on-surface" id="email" name="email" placeholder="patient@example.com" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />

              </div>

            </div>
            <div className="space-y-2">

              <div className="flex justify-between items-center px-1">

                <label className="font-label-md text-label-md text-on-surface-variant" htmlFor="password">Password</label>
                <a className="font-label-md text-label-md text-secondary hover:underline" href="#">Forgot?</a>

              </div>
              <div className="relative group input-focus-glow rounded-xl transition-all">

                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">

                  <span className="material-symbols-outlined text-outline">lock</span>

                </div>
                <input className="block w-full h-14 pl-12 pr-4 bg-surface-container-low border-none rounded-xl font-body-md text-body-md focus:ring-2 focus:ring-primary-fixed-dim transition-all text-on-surface" id="password" name="password" placeholder="••••••••" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />

              </div>

            </div>
            <div className="pt-2">

              <button className="w-full h-14 bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md rounded-xl transition-all transform active:scale-[0.98] shadow-md flex items-center justify-center gap-2 group" type="submit">

                        Login
                                        <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">arrow_forward</span>

              </button>

            </div>

          </form>
          <div className="mt-8 text-center">

            <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => {
                  setEmail("patient@vithara.com");
                  setPassword("Password123!");
                }}
                className="inline-flex h-11 items-center justify-center rounded-xl border border-emerald-300 bg-emerald-50 px-3 text-xs font-bold text-emerald-900 hover:bg-emerald-100 transition-all"
              >
                ⚡ 1-Click Patient Demo
              </button>
              <button
                type="button"
                onClick={() => {
                  setEmail("doctor@vithara.com");
                  setPassword("Password123!");
                }}
                className="inline-flex h-11 items-center justify-center rounded-xl border border-blue-300 bg-blue-50 px-3 text-xs font-bold text-blue-900 hover:bg-blue-100 transition-all"
              >
                ⚡ 1-Click Doctor Demo
              </button>
            </div>

            <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Link
                to="/patient/login"
                className="inline-flex h-12 items-center justify-center rounded-xl border border-primary-fixed-dim bg-surface-mint px-4 font-label-md text-label-md text-primary hover:bg-primary hover:text-on-primary transition-all"
              >
                Patient Portal
              </Link>
              <Link
                to="/doctor/login"
                className="inline-flex h-12 items-center justify-center rounded-xl border border-primary-fixed-dim bg-surface-container-low px-4 font-label-md text-label-md text-primary hover:bg-primary hover:text-on-primary transition-all"
              >
                Doctor Portal
              </Link>
            </div>

            <div className="space-y-4 mb-8">
              <p className="font-body-md text-body-md text-on-surface-variant">New to Vithara?</p>
              <Link to={registerPath} className="inline-flex w-full h-14 items-center justify-center border-2 border-primary text-primary font-label-md text-label-md rounded-xl hover:bg-primary hover:text-on-primary transition-all transform active:scale-[0.98]">Create a new account</Link>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Link to="/patient/register" className="text-sm font-semibold text-secondary hover:underline">Register as patient</Link>
                <Link to="/doctor/register" className="text-sm font-semibold text-secondary hover:underline">Register as doctor</Link>
              </div>
            </div>
            <div className="flex flex-col items-center gap-2 mt-4">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-surface-mint rounded-full border border-primary-fixed-dim/30">
                <span className="material-symbols-outlined text-alert-low text-sm" style={{ "fontVariationSettings": "'FILL' 1" }}>verified_user</span>
                <span className="font-caption text-caption text-on-primary-fixed-variant tracking-wide">Secure patient access</span>
              </div>

              {/* Mobile / Localhost Server Config Link */}
              <button
                type="button"
                onClick={() => {
                  setShowConfig(true);
                  handlePing(serverUrl);
                }}
                className="mt-2 inline-flex items-center gap-1.5 text-xs text-[#667064] hover:text-[#061907] transition-colors underline"
              >
                <span>🌐 Server: <span className="font-mono font-medium">{serverUrl}</span></span>
                <span>(Change)</span>
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
                <h3 className="text-base font-bold text-[#061907]">Server Connection Settings</h3>
                <p className="text-xs text-[#667064]">Configure backend API address for Android or local network</p>
              </div>
              <button
                type="button"
                onClick={() => setShowConfig(false)}
                className="rounded-lg p-1 text-[#667064] hover:bg-gray-100"
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
                  placeholder="http://10.206.162.226:8000"
                  className="w-full rounded-xl border border-[#cbdcc7] px-3.5 py-2.5 text-sm font-mono text-[#061907] focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                />
              </div>

              {/* Quick Presets */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-bold text-[#667064] uppercase tracking-wider">Quick Presets:</span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleResetServer("http://10.206.162.226:8000")}
                    className="rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-left text-xs font-semibold text-emerald-900 hover:bg-emerald-100 transition-all"
                  >
                    📡 Wi-Fi Host IP
                    <div className="text-[10px] font-mono text-emerald-700 truncate">10.206.162.226:8000</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleResetServer("http://127.0.0.1:8000")}
                    className="rounded-lg border border-gray-300 bg-gray-50 px-2.5 py-1.5 text-left text-xs font-semibold text-gray-800 hover:bg-gray-100 transition-all"
                  >
                    💻 Localhost
                    <div className="text-[10px] font-mono text-gray-600 truncate">127.0.0.1:8000</div>
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
                    className="rounded-lg bg-gray-200 px-2.5 py-1 text-[11px] font-bold text-gray-800 hover:bg-gray-300 transition-all"
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
                className="rounded-xl border border-gray-300 px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveServer}
                className="rounded-xl bg-[#061907] px-5 py-2 text-xs font-bold text-white shadow hover:bg-emerald-950"
              >
                Save & Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
