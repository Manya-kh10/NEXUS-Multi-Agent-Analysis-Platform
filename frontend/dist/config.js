// Global configuration variables for NEXUS
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "8501";
// Production Render API endpoint resolver
const API_URL = localStorage.getItem("NEXUS_API_URL") || (isLocal ? "http://localhost:8000" : "https://nexus-backend-render.onrender.com");
