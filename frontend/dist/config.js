// Global configuration variables for NEXUS
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "8501";

// Production Render API endpoint resolver using Vite env or localStorage fallback
let rawApiUrl = localStorage.getItem("NEXUS_API_URL") || import.meta.env.VITE_API_URL || (isLocal ? "http://localhost:8000" : "https://nexus-backend-render.onrender.com");

// Sanitize URL: Remove trailing slashes and /api prefix if present to prevent double-prefixing (e.g., /api/api/...)
if (rawApiUrl.endsWith("/")) {
  rawApiUrl = rawApiUrl.slice(0, -1);
}
if (rawApiUrl.endsWith("/api")) {
  rawApiUrl = rawApiUrl.slice(0, -4);
}

const API_URL = rawApiUrl;
