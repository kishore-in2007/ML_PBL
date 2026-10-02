import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export default function ProtectedRoute({ allowedRoles }) {
  const token = localStorage.getItem("token");
  const userString = localStorage.getItem("user");
  const location = useLocation();

  if (!token) {
    const loginPath = allowedRoles?.includes("patient") ? "/patient/login" : "/doctor/login";
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  let user = {};
  try {
    user = JSON.parse(userString || "{}");
  } catch (e) {
    console.error("Failed to parse user from localStorage", e);
  }

  const role = user.role || "";

  // 10. If role is patient and accessing doctor route, redirect to /patient/dashboard.
  if (allowedRoles.some(r => ["doctor", "nurse", "admin"].includes(r)) && role === "patient") {
    return <Navigate to="/patient/dashboard" replace />;
  }

  // 11. If role is doctor/nurse/admin and accessing patient route, redirect to /doctor/dashboard.
  if (allowedRoles.includes("patient") && ["doctor", "nurse", "admin"].includes(role)) {
    return <Navigate to="/doctor/dashboard" replace />;
  }

  return <Outlet />;
}
