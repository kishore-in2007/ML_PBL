import axios from "axios";

export const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    const custom = localStorage.getItem("vithara_api_url");
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/+$/, "");
    }
    // Check if running inside Capacitor native Android app
    const isCapacitor = Boolean(
      window.Capacitor ||
      window.location.protocol === "capacitor:" ||
      (window.location.hostname === "localhost" && (!window.location.port || window.location.port === "80"))
    );
    if (isCapacitor) {
      return "http://10.206.162.226:8000";
    }
    // Check if accessed through LAN IP on mobile browser
    if (
      window.location.hostname &&
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1"
    ) {
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
  }
  return import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
};

export const API_BASE_URL = getBaseUrl();

const api = axios.create({
  baseURL: getBaseUrl(),
});

api.interceptors.request.use(
  (config) => {
    config.baseURL = getBaseUrl();
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;

