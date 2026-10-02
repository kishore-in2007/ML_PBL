import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/common/Login";
import Register from "./pages/common/Register";
import PatientDashboard from "./pages/patient/PatientDashboard";
import CaptureWoundPhoto from "./pages/patient/CaptureWoundPhoto";
import AIAnalysisResult from "./pages/patient/AIAnalysisResult";
import RecoveryTrends from "./pages/patient/RecoveryTrends";
import Reminders from "./pages/patient/Reminders";
import VoiceAssistant from "./pages/patient/VoiceAssistant";
import CareTeam from "./pages/patient/CareTeam";
import PatientProfile from "./pages/patient/PatientProfile";
import DoctorDashboard from "./pages/doctor/DoctorDashboard";
import PatientRecords from "./pages/doctor/PatientRecords";
import PatientSummary from "./pages/doctor/PatientSummary";
import WoundReview from "./pages/doctor/WoundReview";
import Appointments from "./pages/doctor/Appointments";
import UrgentAlerts from "./pages/doctor/UrgentAlerts";
import ConsultationSession from "./pages/doctor/ConsultationSession";
import DoctorNotifications from "./pages/doctor/DoctorNotifications";
import DoctorProfile from "./pages/doctor/DoctorProfile";

function RootRedirect() {
  const token = localStorage.getItem("token");
  const userString = localStorage.getItem("user");

  if (!token) {
    return <Navigate to="/patient/login" replace />;
  }

  let user = {};
  try {
    user = JSON.parse(userString || "{}");
  } catch (e) {
    console.error("Failed to parse user from localStorage", e);
  }

  const role = user.role || "";
  if (role === "patient") {
    return <Navigate to="/patient/dashboard" replace />;
  } else if (["doctor", "nurse", "admin"].includes(role)) {
    return <Navigate to="/doctor/dashboard" replace />;
  }
  return <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <div>
        <Routes>
          {/* Root redirect depending on authorization */}
          <Route path="/" element={<RootRedirect />} />

          {/* Common routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/patient/login"
            element={
              <Login
                allowedRoles={["patient"]}
                heading="Patient Recovery Monitor"
                subheading="Track your recovery and submit wound updates"
                registerPath="/patient/register"
              />
            }
          />
          <Route
            path="/doctor/login"
            element={
              <Login
                allowedRoles={["doctor", "nurse", "admin"]}
                heading="Doctor Clinical Portal"
                subheading="Review patients, appointments, wounds, and urgent alerts"
                registerPath="/doctor/register"
              />
            }
          />
          <Route
            path="/patient/register"
            element={
              <Register
                fixedRole="patient"
                title="Create Patient Account"
                subtitle="Start your monitored recovery journey"
                loginPath="/patient/login"
              />
            }
          />
          <Route
            path="/doctor/register"
            element={
              <Register
                fixedRole="doctor"
                title="Create Doctor Account"
                subtitle="Set up clinical oversight access"
                loginPath="/doctor/login"
              />
            }
          />

          {/* Patient protected routes */}
          <Route element={<ProtectedRoute allowedRoles={["patient"]} />}>
            <Route path="/patient/dashboard" element={<PatientDashboard />} />
            <Route path="/patient/capture" element={<CaptureWoundPhoto />} />
            <Route path="/patient/analysis-result" element={<AIAnalysisResult />} />
            <Route path="/patient/trends" element={<RecoveryTrends />} />
            <Route path="/patient/reminders" element={<Reminders />} />
            <Route path="/patient/voice-assistant" element={<VoiceAssistant />} />
            <Route path="/patient/care-team" element={<CareTeam />} />
            <Route path="/patient/profile" element={<PatientProfile />} />
          </Route>

          {/* Doctor protected routes */}
          <Route element={<ProtectedRoute allowedRoles={["doctor", "nurse", "admin"]} />}>
            <Route path="/doctor/dashboard" element={<DoctorDashboard />} />
            <Route path="/doctor/patients" element={<PatientRecords />} />
            <Route path="/doctor/patient-summary" element={<PatientSummary />} />
            <Route path="/doctor/wound-review" element={<WoundReview />} />
            <Route path="/doctor/appointments" element={<Appointments />} />
            <Route path="/doctor/urgent-alerts" element={<UrgentAlerts />} />
            <Route path="/doctor/consultation" element={<ConsultationSession />} />
            <Route path="/doctor/notifications" element={<DoctorNotifications />} />
            <Route path="/doctor/profile" element={<DoctorProfile />} />
          </Route>

          {/* Catch-all redirect to root */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
