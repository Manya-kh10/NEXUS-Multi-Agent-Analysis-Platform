// Global configuration variables for NEXUS
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "8501";

// Resolve production API URL: uses injected placeholder from build process, or production Render fallback
const buildTimeApiUrl = "__VITE_API_URL__";
const fallbackApiUrl = buildTimeApiUrl.startsWith("__") ? "https://nexus-multi-agent-analysis-platform.onrender.com" : buildTimeApiUrl;

let rawApiUrl = localStorage.getItem("NEXUS_API_URL") || (isLocal ? "http://localhost:8000" : fallbackApiUrl);

// Sanitize URL: Remove trailing slashes and /api prefix if present to prevent double-prefixing
if (rawApiUrl.endsWith("/")) {
  rawApiUrl = rawApiUrl.slice(0, -1);
}
if (rawApiUrl.endsWith("/api")) {
  rawApiUrl = rawApiUrl.slice(0, -4);
}

const API_URL = rawApiUrl;
