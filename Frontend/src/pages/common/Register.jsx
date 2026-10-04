import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../../api/api";

export default function Register({
  fixedRole = null,
  title = "Create Account",
  subtitle = "Start your recovery journey with care",
  loginPath = "/login",
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState(fixedRole || "patient");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    const resolvedRole = fixedRole || role;
    try {
      await api.post("/auth/register", {
        email,
        password,
        full_name: fullName,
        role: resolvedRole
      });

      // 7. After successful registration, navigate to /login.
      navigate(loginPath);
    } catch (err) {
      console.error(err);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Registration failed. Please make sure the email is valid and try again.");
      }
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-4 sm:p-6 bg-gradient-to-br from-[#eef6f0] via-[#f7faf8] to-[#e8f1eb] relative overflow-x-hidden">
      <div className="fixed top-0 right-0 w-[500px] h-[500px] bg-emerald-100 rounded-full blur-[120px] opacity-40 -mr-48 -mt-48 pointer-events-none"></div>
      <div className="fixed bottom-0 left-0 w-[400px] h-[400px] bg-teal-100 rounded-full blur-[100px] opacity-30 -ml-32 -mb-32 pointer-events-none"></div>
      <header className="w-full max-w-md px-container-padding-mobile mb-6 text-center animate-fade-in relative z-10">

        <div className="inline-flex items-center justify-center mb-6">

          <span className="material-symbols-outlined text-primary text-[40px]" style={{ "fontVariationSettings": "'FILL' 1" }}>healing</span>

        </div>
        <h1 className="font-headline-lg-mobile text-headline-lg-mobile text-primary mb-2">{title}</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">{subtitle}</p>

      </header>
      <main className="w-full max-w-md px-container-padding-mobile animate-in slide-in-from-bottom-4 duration-700">

        <div className="tonal-layer rounded-xl p-8 border border-outline-variant/30">

          <form className="space-y-6" id="register-form" onSubmit={handleSubmit}>
            {error && (
              <div className="p-4 bg-red-50 text-red-800 border border-red-200 rounded-xl text-sm font-body-md animate-fade-in flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">error</span>
                <span>{error}</span>
              </div>
            )}


            <div className="space-y-2">

              <label className="font-label-md text-label-md text-on-surface-variant block ml-1" htmlFor="full-name">Full name</label>
              <div className="relative group">

                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">person</span>
                <input className="w-full h-12 pl-12 pr-4 bg-background-ivory border border-outline-variant rounded-lg font-body-md text-body-md focus:ring-2 focus:ring-surface-tint focus:border-transparent outline-none transition-all placeholder:text-outline-variant" id="full-name" placeholder="John Doe" required type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} />

              </div>

            </div>

            <div className="space-y-2">

              <label className="font-label-md text-label-md text-on-surface-variant block ml-1" htmlFor="email">Email</label>
              <div className="relative group">

                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">mail</span>
                <input className="w-full h-12 pl-12 pr-4 bg-background-ivory border border-outline-variant rounded-lg font-body-md text-body-md focus:ring-2 focus:ring-surface-tint focus:border-transparent outline-none transition-all placeholder:text-outline-variant" id="email" placeholder="john@example.com" required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />

              </div>

            </div>

            <div className="grid grid-cols-1 gap-4">

              <div className="space-y-2">

                <label className="font-label-md text-label-md text-on-surface-variant block ml-1" htmlFor="password">Password</label>
                <div className="relative">

                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">lock</span>
                  <input className="w-full h-12 pl-12 pr-4 bg-background-ivory border border-outline-variant rounded-lg font-body-md text-body-md focus:ring-2 focus:ring-surface-tint focus:border-transparent outline-none transition-all placeholder:text-outline-variant" id="password" placeholder="••••••••" required type="password" value={password} onChange={(e) => setPassword(e.target.value)} />

                </div>

              </div>
              <div className="space-y-2">

                <label className="font-label-md text-label-md text-on-surface-variant block ml-1" htmlFor="confirm-password">Confirm password</label>
                <div className="relative">

                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">verified_user</span>
                  <input className="w-full h-12 pl-12 pr-4 bg-background-ivory border border-outline-variant rounded-lg font-body-md text-body-md focus:ring-2 focus:ring-surface-tint focus:border-transparent outline-none transition-all placeholder:text-outline-variant" id="confirm-password" placeholder="••••••••" required type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />

                </div>

              </div>

            </div>

            {!fixedRole && <div className="space-y-3">

              <span className="font-label-md text-label-md text-on-surface-variant block ml-1">I am a...</span>
              <div className="flex gap-4">

                <label className="flex-1 cursor-pointer group">

                  <input checked={role === "patient"} onChange={() => setRole("patient")} className="sr-only peer" name="role" type="radio" value="patient" />
                  <div className="flex flex-col items-center justify-center p-3 rounded-lg border border-outline-variant bg-background-ivory peer-checked:border-secondary peer-checked:bg-secondary-fixed transition-all active:scale-95">

                    <span className="material-symbols-outlined text-on-surface peer-checked:text-secondary mb-1">person_play</span>
                    <span className="font-label-md text-label-md">Patient</span>

                  </div>

                </label>
                <label className="flex-1 cursor-pointer group">

                  <input checked={role === "doctor"} onChange={() => setRole("doctor")} className="sr-only peer" name="role" type="radio" value="doctor" />
                  <div className="flex flex-col items-center justify-center p-3 rounded-lg border border-outline-variant bg-background-ivory peer-checked:border-secondary peer-checked:bg-secondary-fixed transition-all active:scale-95">

                    <span className="material-symbols-outlined text-on-surface peer-checked:text-secondary mb-1">medical_services</span>
                    <span className="font-label-md text-label-md">Doctor</span>

                  </div>

                </label>

              </div>

            </div>}

            <button className="w-full h-12 bg-primary text-on-primary font-label-md text-label-md rounded-full shadow-sm hover:opacity-90 active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-4" type="submit">

                    Create Account
                                  <span className="material-symbols-outlined text-[20px]">arrow_forward</span>

            </button>

          </form>

          <div className="mt-8 pt-6 border-t border-outline-variant/30 text-center space-y-4">

            <p className="font-body-md text-body-md text-on-surface-variant">

                    Already have an account? 
                                  <Link className="text-secondary font-semibold hover:underline transition-all" to={loginPath}>Login</Link>

            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Link to="/patient/login" className="inline-flex h-11 items-center justify-center rounded-lg border border-outline-variant bg-background-ivory text-sm font-semibold text-primary hover:bg-surface-mint">
                Patient Login
              </Link>
              <Link to="/doctor/login" className="inline-flex h-11 items-center justify-center rounded-lg border border-outline-variant bg-background-ivory text-sm font-semibold text-primary hover:bg-surface-mint">
                Doctor Login
              </Link>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Link to="/patient/register" className="text-sm font-semibold text-secondary hover:underline">Patient registration</Link>
              <Link to="/doctor/register" className="text-sm font-semibold text-secondary hover:underline">Doctor registration</Link>
            </div>
            <div className="flex items-center justify-center gap-2 px-4 py-2 bg-surface-container-low rounded-full inline-flex">

              <span className="material-symbols-outlined text-alert-low text-[18px]">security</span>
              <span className="font-caption text-caption text-on-surface-variant">Your health data is stored securely</span>

            </div>

          </div>

        </div>

        <div className="mt-8 flex justify-center items-center gap-2 opacity-50">

          <div className="w-8 h-1 bg-primary rounded-full"></div>
          <div className="w-2 h-1 bg-outline-variant rounded-full"></div>
          <div className="w-2 h-1 bg-outline-variant rounded-full"></div>

        </div>

      </main>
      <footer className="mt-6 py-4 text-center px-4 relative z-10">
        <p className="font-caption text-caption text-outline">© 2024 Vithara Recovery Monitor. All Rights Reserved.</p>
      </footer>
    </div>
  );
}
