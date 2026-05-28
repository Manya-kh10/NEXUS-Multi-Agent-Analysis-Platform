import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        upload: resolve(__dirname, 'upload.html'),
        analysis: resolve(__dirname, 'analysis.html'),
        chat: resolve(__dirname, 'chat.html'),
        history: resolve(__dirname, 'history.html'),
        profile: resolve(__dirname, 'profile.html'),
        register: resolve(__dirname, 'register.html'),
        support: resolve(__dirname, 'support.html'),
        changePassword: resolve(__dirname, 'change-password.html'),
      }
    }
  }
});
