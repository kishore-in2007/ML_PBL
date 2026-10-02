import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Activity, Bell, CalendarDays, Camera, FileText, Home, LogOut, Mic, Siren, Stethoscope, UserRound, UsersRound, Wifi } from "lucide-react";
import { getStoredUser, logout } from "../api/helpers";
import { getBaseUrl } from "../api/api";

const patientNav = [
  { to: "/patient/dashboard", label: "Home", icon: Home },
  { to: "/patient/capture", label: "Capture", icon: Camera },
  { to: "/patient/trends", label: "Trends", icon: Activity },
  { to: "/patient/reminders", label: "Reminders", icon: Bell },
  { to: "/patient/care-team", label: "Care Team", icon: Stethoscope },
  { to: "/patient/voice-assistant", label: "Assistant", icon: Mic },
  { to: "/patient/profile", label: "Profile", icon: UserRound },
];

const doctorNav = [
  { to: "/doctor/dashboard", label: "Dashboard", icon: Home },
  { to: "/doctor/patients", label: "Patients", icon: UsersRound },
  { to: "/doctor/appointments", label: "Appointments", icon: CalendarDays },
  { to: "/doctor/urgent-alerts", label: "Urgent", icon: Siren },
  { to: "/doctor/notifications", label: "Notifications", icon: Bell },
  { to: "/doctor/wound-review", label: "Wound Review", icon: FileText },
];

export default function AppShell({ role = "patient", title, children, actions }) {
  const navigate = useNavigate();
  const user = getStoredUser();
  const navItems = role === "doctor" ? doctorNav : patientNav;

  return (
    <div className="min-h-screen bg-[#fdf9f3] text-[#1c1c18]">
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 flex-col border-r border-[#e4dfd7] bg-white/80 px-5 py-6">
        <div className="mb-8">
          <p className="text-2xl font-bold text-[#061907]">Vithara</p>
          <p className="mt-1 text-sm text-[#667064]">{role === "doctor" ? "Clinical portal" : "Recovery monitor"}</p>
        </div>
        <nav className="space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-semibold transition ${
                  isActive ? "bg-[#061907] text-white" : "text-[#4d574b] hover:bg-[#ebf2ec]"
                }`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => logout(navigate, role)}
          className="mt-auto flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-semibold text-red-700 hover:bg-red-50"
        >
          <LogOut size={18} />
          Logout
        </button>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-[#e4dfd7] bg-[#fdf9f3]/95 px-4 py-4 backdrop-blur md:px-8">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[#667064]">
                {role === "doctor" ? "Doctor workspace" : "Patient workspace"}
              </p>
              <h1 className="text-xl font-bold text-[#061907] md:text-2xl">{title}</h1>
            </div>
            <div className="flex items-center gap-3">
              {actions}
              <div className="hidden text-right sm:block">
                <p className="text-sm font-semibold text-[#1c1c18]">{user.email || "Signed in"}</p>
                <p className="text-xs capitalize text-[#667064]">{user.role || role}</p>
              </div>
              <button
                onClick={() => {
                  const current = localStorage.getItem("vithara_api_url") || getBaseUrl();
                  const nextUrl = window.prompt("Vithara Backend API URL:\n(Enter your PC's Wi-Fi IP address with port 8000, e.g. http://10.206.162.226:8000)", current);
                  if (nextUrl !== null && nextUrl.trim()) {
                    localStorage.setItem("vithara_api_url", nextUrl.trim().replace(/\/+$/, ""));
                    window.location.reload();
                  }
                }}
                className="rounded-lg border border-[#d8d2c8] p-2 text-[#4d574b] hover:bg-white"
                title={`Server: ${getBaseUrl()} (Click to change)`}
              >
                <Wifi size={18} className="text-emerald-700" />
              </button>
              <button
                onClick={() => logout(navigate, role)}
                className="rounded-lg border border-[#d8d2c8] p-2 text-[#4d574b] hover:bg-white"
                title="Logout"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 pb-24 md:px-8">{children}</main>
      </div>

      <nav className="fixed bottom-0 left-0 right-0 z-40 grid grid-cols-4 border-t border-[#e4dfd7] bg-white px-2 py-2 shadow-lg lg:hidden">
        {navItems.slice(0, 4).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 rounded-lg px-2 py-2 text-xs font-semibold ${
                isActive ? "bg-[#061907] text-white" : "text-[#667064]"
              }`
            }
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {role === "patient" && (
        <button
          onClick={() => navigate("/patient/voice-assistant")}
          className="fixed bottom-24 right-5 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-[#061907] text-white shadow-lg hover:bg-[#153315] lg:bottom-6"
          title="Voice Assistant"
          aria-label="Voice Assistant"
        >
          <Mic size={22} />
        </button>
      )}
    </div>
  );
}

export function StatCard({ label, value, tone = "default", icon: Icon }) {
  const tones = {
    default: "border-[#e4dfd7] bg-white",
    good: "border-[#cbdcc7] bg-[#ebf2ec]",
    warn: "border-[#f1d0b8] bg-[#fff4ec]",
    danger: "border-[#f1b8b8] bg-[#fff1f1]",
  };

  return (
    <section className={`rounded-xl border p-5 shadow-sm ${tones[tone] || tones.default}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#667064]">{label}</p>
          <p className="mt-2 text-3xl font-bold text-[#061907]">{value}</p>
        </div>
        {Icon && <Icon className="text-[#4e644c]" size={24} />}
      </div>
    </section>
  );
}

export function EmptyState({ title, message }) {
  return (
    <div className="rounded-xl border border-dashed border-[#d8d2c8] bg-white p-6 text-center">
      <p className="font-semibold text-[#061907]">{title}</p>
      <p className="mt-1 text-sm text-[#667064]">{message}</p>
    </div>
  );
}
