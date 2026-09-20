import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Runs in its own container (see Dockerfile), alongside the three backend
// services, but still talks to them directly over HTTP from the browser —
// nothing in this project proxies or builds this client server-side.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 0.0.0.0 so the dev server accepts connections from outside the
    // container (the default, 127.0.0.1-only, is unreachable even with the
    // port published in docker-compose.yml). The CMD in the Dockerfile also
    // passes --host, which is belt-and-suspenders with this.
    host: true,
    strictPort: true,
  },
});
