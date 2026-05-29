// Shared common logic for NEXUS authenticated pages
document.addEventListener("DOMContentLoaded", () => {
  // Auth Guard - Optional Guest Session
  const token = localStorage.getItem("nexus_jwt_token");
  const isLoginPage = window.location.pathname === "/" || window.location.pathname === "/index.html" || window.location.pathname.endsWith("/register") || window.location.pathname.endsWith("/register.html");
  
  if (!token) {
    if (isLoginPage) {
      // Allow visitor to view login/register pages
    } else {
      // Set Guest profile in the DOM
      const nameElements = document.querySelectorAll(".user-name-display, #user-name-display");
      nameElements.forEach(el => el.textContent = "Guest Operative");

      const emailElements = document.querySelectorAll(".user-email-display, #user-email-display");
      emailElements.forEach(el => el.textContent = "guest@nexus.core");

      const initialElements = document.querySelectorAll(".user-avatar-initials, #user-avatar-initials");
      initialElements.forEach(el => el.textContent = "G");

      const roleElements = document.querySelectorAll(".user-role-display, #user-role-display");
      roleElements.forEach(el => el.textContent = "Guest");

      // Replace logout button with "Sign In"
      const logoutButtons = document.querySelectorAll(".logout-btn, #logout-btn");
      logoutButtons.forEach(btn => {
        btn.innerHTML = `<span class="material-symbols-outlined text-[18px]">login</span> Sign In`;
        btn.classList.remove("hover:bg-error/10", "hover:text-error", "hover:border-error/30");
        btn.classList.add("hover:bg-primary/10", "hover:text-primary", "hover:border-primary/30");
        
        // Remove event listeners by replacing the element or override onclick
        btn.onclick = (e) => {
          e.preventDefault();
          window.location.href = "/";
        };
      });
    }
  }

  // Populate dynamic user info across the DOM
  const storedUser = localStorage.getItem("nexus_user");
  if (storedUser) {
    try {
      const user = JSON.parse(storedUser);
      
      // User name displays
      const nameElements = document.querySelectorAll(".user-name-display, #user-name-display");
      nameElements.forEach(el => {
        el.textContent = user.username || "Operative";
      });

      // User email displays
      const emailElements = document.querySelectorAll(".user-email-display, #user-email-display");
      emailElements.forEach(el => {
        el.textContent = user.email || "operator@nexus.core";
      });

      // User initials displays
      const initialElements = document.querySelectorAll(".user-avatar-initials, #user-avatar-initials");
      initialElements.forEach(el => {
        el.textContent = user.username ? user.username.charAt(0).toUpperCase() : "O";
      });

      // User role displays
      const roleElements = document.querySelectorAll(".user-role-display, #user-role-display");
      roleElements.forEach(el => {
        el.textContent = user.is_admin ? "Admin" : "Operative";
      });

    } catch (e) {
      console.error("Failed to parse user session details:", e);
    }
  }

  // Populate custom profile details from localStorage if they exist
  const storedProfile = localStorage.getItem("nexus_profile");
  if (storedProfile) {
    try {
      const profile = JSON.parse(storedProfile);
      if (profile.fullName) {
        document.querySelectorAll(".user-name-display").forEach(el => el.textContent = profile.fullName);
      }
      if (profile.email) {
        document.querySelectorAll(".user-email-display").forEach(el => el.textContent = profile.email);
      }
      if (profile.role) {
        document.querySelectorAll(".user-role-display").forEach(el => el.textContent = profile.role);
      }
    } catch (e) {
      console.error("Failed to parse custom profile info:", e);
    }
  }

  // Dynamic avatar image replacement
  const customAvatar = localStorage.getItem("nexus_avatar");
  if (customAvatar) {
    const initialElements = document.querySelectorAll(".user-avatar-initials, #user-avatar-initials");
    initialElements.forEach(el => {
      el.innerHTML = `<img src="${customAvatar}" class="w-full h-full rounded-full object-cover" />`;
      el.classList.remove("bg-primary/20", "bg-primary", "text-primary", "text-on-primary", "border-primary/20");
    });
  }

  // Attach logout handler to any logout buttons
  const logoutButtons = document.querySelectorAll(".logout-btn, #logout-btn");
  logoutButtons.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      handleLogout();
    });
  });

  // Welcome Toast trigger (runs once per session on dashboard load)
  const isDashboard = window.location.pathname.endsWith("/dashboard") || window.location.pathname === "/dashboard";
  if (isDashboard) {
    const toastShown = sessionStorage.getItem("nexus_toast_shown");
    if (!toastShown) {
      sessionStorage.setItem("nexus_toast_shown", "true");
      const toast = document.getElementById("welcome-toast");
      if (toast) {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
        setTimeout(() => {
          toast.style.opacity = "0";
          setTimeout(() => toast.remove(), 500);
        }, 5000);
      }
    } else {
      // Remove welcome toast from layout immediately if already shown in session
      document.getElementById("welcome-toast")?.remove();
    }
  }
});

// Helper to construct authorization headers for fetch requests
function getAuthHeaders(contentType = "application/json") {
  const token = localStorage.getItem("nexus_jwt_token");
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  return headers;
}

// Session log out handler
function handleLogout() {
  localStorage.removeItem("nexus_jwt_token");
  localStorage.removeItem("nexus_user");
  sessionStorage.removeItem("nexus_toast_shown");
  window.location.href = "/";
}

// Global fetch interceptor to catch 401 Unauthorized and redirect to login gracefully
const originalFetch = window.fetch;
window.fetch = async function (...args) {
  try {
    const response = await originalFetch.apply(this, args);
    if (response.status === 401) {
      localStorage.removeItem("nexus_jwt_token");
      localStorage.removeItem("nexus_user");
      
      const isLoginPage = window.location.pathname === "/" || window.location.pathname === "/index.html" || window.location.pathname.endsWith("/register") || window.location.pathname.endsWith("/register.html");
      if (!isLoginPage) {
        alert("Session Expired: Your security token has expired or is invalid. Please sign in again.");
        window.location.href = "/";
      }
    }
    return response;
  } catch (error) {
    throw error;
  }
};
