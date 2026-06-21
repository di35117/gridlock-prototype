import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(),tailwindcss()],
  server: {
    // THIS IS THE BYPASS: Intercepts MapmyIndia requests and masks the Origin
    proxy: {
      "/mapmyindia": {
        target: "https://apis.mapmyindia.com",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/mapmyindia/, ""),
      },
    },
  },
});
