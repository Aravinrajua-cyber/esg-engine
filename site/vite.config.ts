import fs from "node:fs";
import path from "node:path";
import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = path.resolve(__dirname, "..");
const siteDataDir = path.join(repoRoot, "outputs", "site_data");

function siteDataPlugin(): Plugin {
  return {
    name: "site-data-bridge",
    configureServer(server) {
      server.middlewares.use("/site_data", (req, res, next) => {
        const url = req.url?.split("?")[0] || "/";
        const filePath = path.normalize(path.join(siteDataDir, url));
        if (!filePath.startsWith(siteDataDir) || !fs.existsSync(filePath)) {
          next();
          return;
        }
        res.setHeader("Content-Type", "application/json");
        fs.createReadStream(filePath).pipe(res);
      });
    },
    closeBundle() {
      const outDir = path.join(__dirname, "dist", "site_data");
      if (fs.existsSync(siteDataDir)) {
        fs.mkdirSync(outDir, { recursive: true });
        for (const file of fs.readdirSync(siteDataDir)) {
          if (file.endsWith(".json")) {
            fs.copyFileSync(path.join(siteDataDir, file), path.join(outDir, file));
          }
        }
      }
    }
  };
}

export default defineConfig({
  plugins: [react(), siteDataPlugin()],
  build: {
    target: "es2022",
    sourcemap: false
  }
});
