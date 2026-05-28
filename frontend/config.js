// Global configuration variables for NEXUS
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "8501";
// Relative path origin in cloud environments to leverage Vercel's rewrite proxy and bypass CORS
const API_URL = localStorage.getItem("NEXUS_API_URL") || (isLocal ? "http://localhost:8000" : window.location.origin);
