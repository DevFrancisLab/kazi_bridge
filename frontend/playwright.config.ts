import type { PlaywrightTestConfig } from "@playwright/test";
import { defineConfig } from "@playwright/test";

const config: PlaywrightTestConfig = {
  timeout: 60000,
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
  },
};

export default defineConfig(config);
