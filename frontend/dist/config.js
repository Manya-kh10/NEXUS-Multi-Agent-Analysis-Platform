// Global configuration variables for NEXUS
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "8501";

// Simple global config approach
const API_URL = isLocal ? "http://localhost:8000" : "https://nexus-multi-agent-analysis-platform.onrender.com";
