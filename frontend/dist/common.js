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
    }
  }

  // --- RESPONSIVE SIDEBAR COLLAPSE & MOBILE SLIDEOUT ---
  // Injected responsive layout styling for premium look & animations
  const style = document.createElement("style");
  style.innerHTML = `
    /* Transitions for smooth premium feel */
    aside {
      transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    header, main, footer {
      transition: margin-left 0.35s cubic-bezier(0.4, 0, 0.2, 1), left 0.35s cubic-bezier(0.4, 0, 0.2, 1), width 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    @media (max-width: 1024px) {
      aside {
        transform: translateX(-100%);
        box-shadow: none;
      }
      aside.sidebar-open {
        transform: translateX(0);
        box-shadow: 10px 0 35px rgba(0, 0, 0, 0.6);
      }
      header {
        margin-left: 0 !important;
        width: 100% !important;
      }
      main {
        margin-left: 0 !important;
        padding: 16px !important;
        width: 100% !important;
      }
      footer {
        left: 0 !important;
        width: 100% !important;
      }
    }
    
    /* Collapsed Sidebar on Desktop */
    body.sidebar-collapsed aside {
      transform: translateX(-100%);
    }
    body.sidebar-collapsed header {
      margin-left: 0 !important;
      width: 100% !important;
    }
    body.sidebar-collapsed main {
      margin-left: 0 !important;
      width: 100% !important;
    }
    body.sidebar-collapsed footer {
      left: 0 !important;
      width: 100% !important;
    }
  `;
  document.head.appendChild(style);

  // 1. Mobile Logo/Menu Toggle Button on Top Header (with a beautiful mini Nexus logo)
  const header = document.querySelector("header");
  if (header) {
    if (!document.getElementById("mobile-menu-btn")) {
      const menuBtn = document.createElement("button");
      menuBtn.id = "mobile-menu-btn";
      menuBtn.className = "lg:hidden flex items-center gap-2 p-1 hover:bg-surface-container-highest rounded-lg transition-all mr-md text-on-surface cursor-pointer border border-outline-variant/10 bg-surface-container-low px-2 py-1 purple-glow active:scale-95 duration-150";
      menuBtn.innerHTML = `
        <div class="w-7 h-7 rounded bg-primary-container flex items-center justify-center">
          <span class="material-symbols-outlined text-on-primary-container text-[16px]" style="font-variation-settings: 'FILL' 1;">terminal</span>
        </div>
        <span class="text-body-sm font-black text-primary tracking-wider leading-none">NEXUS</span>
      `;
      
      header.insertBefore(menuBtn, header.firstChild);
      
      menuBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const aside = document.querySelector("aside");
        aside?.classList.toggle("sidebar-open");
      });
    }

    // 2. Desktop Toggle Button next to search bar
    if (!document.getElementById("desktop-sidebar-btn")) {
      const deskBtn = document.createElement("button");
      deskBtn.id = "desktop-sidebar-btn";
      deskBtn.className = "hidden lg:flex p-2 hover:bg-surface-container-highest rounded-full transition-colors text-on-surface mr-sm items-center justify-center cursor-pointer";
      deskBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">menu_open</span>`;
      
      const searchWrapper = header.querySelector(".relative");
      if (searchWrapper) {
        searchWrapper.parentNode.insertBefore(deskBtn, searchWrapper);
      } else {
        header.insertBefore(deskBtn, header.firstChild);
      }
      
      deskBtn.addEventListener("click", () => {
        document.body.classList.toggle("sidebar-collapsed");
        const isCollapsed = document.body.classList.contains("sidebar-collapsed");
        deskBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">${isCollapsed ? 'menu' : 'menu_open'}</span>`;
      });
    }
  }

  // 3. Make Left Sidebar Logo a toggle close button!
  const logoContainer = document.querySelector("aside div.px-md.mb-xl div.flex.items-center");
  if (logoContainer) {
    logoContainer.classList.add("cursor-pointer", "hover:opacity-85", "transition-opacity", "relative", "pr-8");
    
    // Add close button/chevron next to the logo
    const toggleIcon = document.createElement("span");
    toggleIcon.className = "material-symbols-outlined absolute right-0 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px] hover:text-primary transition-colors";
    toggleIcon.textContent = "chevron_left";
    logoContainer.appendChild(toggleIcon);
    
    logoContainer.addEventListener("click", () => {
      const aside = document.querySelector("aside");
      if (window.innerWidth <= 1024) {
        aside?.classList.remove("sidebar-open");
      } else {
        document.body.classList.toggle("sidebar-collapsed");
        const deskBtn = document.getElementById("desktop-sidebar-btn");
        if (deskBtn) {
          const isCollapsed = document.body.classList.contains("sidebar-collapsed");
          deskBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">${isCollapsed ? 'menu' : 'menu_open'}</span>`;
        }
      }
    });
  }

  // 4. Click outside to dismiss sidebar on mobile
  document.addEventListener("click", (e) => {
    const aside = document.querySelector("aside");
    const mobileBtn = document.getElementById("mobile-menu-btn");
    if (aside && aside.classList.contains("sidebar-open")) {
      if (!aside.contains(e.target) && (!mobileBtn || !mobileBtn.contains(e.target))) {
        aside.classList.remove("sidebar-open");
      }
    }
  });
});

// Guest Session ID generation/retrieval
let guestSessionId = localStorage.getItem("nexus_guest_session_id");
if (!guestSessionId) {
  guestSessionId = "guest_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  localStorage.setItem("nexus_guest_session_id", guestSessionId);
}

// Helper to construct authorization headers for fetch requests
function getAuthHeaders(contentType = "application/json") {
  const token = localStorage.getItem("nexus_jwt_token");
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const gsId = localStorage.getItem("nexus_guest_session_id");
  if (gsId) {
    headers["X-Guest-Session-ID"] = gsId;
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
      const hasToken = localStorage.getItem("nexus_jwt_token") !== null;
      localStorage.removeItem("nexus_jwt_token");
      localStorage.removeItem("nexus_user");
      
      const isLoginPage = window.location.pathname === "/" || window.location.pathname === "/index.html" || window.location.pathname.endsWith("/register") || window.location.pathname.endsWith("/register.html");
      if (!isLoginPage) {
        if (hasToken) {
          alert("Session Expired: Your security token has expired or is invalid. Please sign in again.");
        } else {
          alert("Access Denied: This operation requires authentication. Please sign in to create an operative session.");
        }
        window.location.href = "/";
      }
    }
    return response;
  } catch (error) {
    throw error;
  }
};
