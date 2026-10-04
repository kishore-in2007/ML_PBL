import axios from "axios";

export const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    // 1. Stored user preference in browser
    const custom = localStorage.getItem("vithara_api_url");
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/+$/, "");
    }

    // 2. Vite environment variable (set in Vercel project settings or .env)
    const envUrl = import.meta.env.VITE_API_BASE_URL;
    if (envUrl && envUrl.trim()) {
      return envUrl.trim().replace(/\/+$/, "");
    }

    // 3. Capacitor native Android app runtime
    const isCapacitor = Boolean(
      window.Capacitor ||
      window.location.protocol === "capacitor:" ||
      (window.location.hostname === "localhost" && (!window.location.port || window.location.port === "80"))
    );
    if (isCapacitor) {
      return "http://10.206.162.226:8000";
    }

    // 4. Access via local private LAN IP (e.g. 192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    const hostname = window.location.hostname || "";
    const isLanIp = /^(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})$/.test(hostname);
    if (isLanIp) {
      return `${window.location.protocol}//${hostname}:8000`;
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

