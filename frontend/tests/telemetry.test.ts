import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
});

describe("frontend telemetry privacy", () => {
  it("removes sensitive values from analytics properties", async () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("PROD", false);
    const { sanitizeAnalyticsProperties } = await import("../src/lib/telemetry");

    const sanitized = sanitizeAnalyticsProperties({
      project_id: "project-1",
      message: "SECRET REQUIREMENT TEXT",
      authorization: "Bearer secret-token",
      reviewer_note: "reviewer confidential note",
      requirement_count: 3,
    });

    expect(sanitized.project_id).toBe("project-1");
    expect(sanitized.requirement_count).toBe(3);
    expect(JSON.stringify(sanitized)).not.toContain("SECRET REQUIREMENT TEXT");
    expect(JSON.stringify(sanitized)).not.toContain("Bearer secret-token");
    expect(JSON.stringify(sanitized)).not.toContain("reviewer confidential note");
  });

  it("filters sensitive Sentry event fields", async () => {
    const { beforeSend } = await import("../src/lib/errorMonitoring");
    const event = beforeSend({
      request: {
        headers: { authorization: "Bearer secret-token", cookie: "session=secret", "x-request-id": "request-1" },
        data: { requirement: "SECRET REQUIREMENT TEXT" },
      },
      extra: { refresh_token: "secret", safe: "ok" },
    });

    expect(event?.request?.headers?.authorization).toBe("[Filtered]");
    expect(event?.request?.headers?.cookie).toBe("[Filtered]");
    expect(event?.request?.data).toBe("[Filtered]");
    expect(event?.extra?.refresh_token).toBe("[Filtered]");
    expect(event?.extra?.safe).toBe("ok");
    expect(JSON.stringify(event)).not.toContain("SECRET REQUIREMENT TEXT");
    expect(JSON.stringify(event)).not.toContain("Bearer secret-token");
  });
});
