import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
});

describe("frontend runtime config", () => {
  it("fails clearly in production when VITE_API_URL is missing", async () => {
    vi.stubEnv("PROD", true);
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_API_URL", "");
    vi.stubEnv("VITE_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "anon");

    const { frontendConfig } = await import("../src/lib/config");

    expect(frontendConfig.apiUrl).toBe("");
    expect(frontendConfig.authConfigError).toContain("VITE_API_URL");
  });

  it("keeps the localhost API fallback for development", async () => {
    vi.stubEnv("PROD", false);
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_API_URL", "");
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "");

    const { frontendConfig } = await import("../src/lib/config");

    expect(frontendConfig.apiUrl).toBe("http://localhost:8000");
    expect(frontendConfig.authConfigError).toBeNull();
  });
});
