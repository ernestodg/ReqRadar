import posthog from "posthog-js";
import { frontendConfig } from "./config";

type AnalyticsProperties = Record<string, string | number | boolean | null | undefined>;

const blockedKeys = new Set(["message", "reviewer_note", "csv_text", "filename", "authorization", "token", "password"]);
const sensitiveMarkers = ["SECRET REQUIREMENT TEXT", "Bearer ", "reviewer confidential note"];

export function sanitizeAnalyticsProperties(properties: AnalyticsProperties = {}) {
  const clean: AnalyticsProperties = {
    environment: frontendConfig.sentryEnvironment,
    release: frontendConfig.sentryRelease,
  };
  for (const [key, value] of Object.entries(properties)) {
    if (blockedKeys.has(key)) continue;
    if (typeof value === "string" && sensitiveMarkers.some((marker) => value.includes(marker))) continue;
    clean[key] = value;
  }
  return clean;
}

export function initAnalytics() {
  if (!frontendConfig.telemetryEnabled || !frontendConfig.posthogKey) return;
  try {
    posthog.init(frontendConfig.posthogKey, {
      api_host: frontendConfig.posthogHost,
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: true,
      persistence: "localStorage+cookie",
      sanitize_properties: (properties) => sanitizeAnalyticsProperties(properties as AnalyticsProperties),
    });
  } catch {
    return;
  }
}

export function identifyAnalyticsUser(userId: string | undefined) {
  if (!frontendConfig.telemetryEnabled || !userId) return;
  try {
    posthog.identify(userId);
  } catch {
    return;
  }
}

export function captureAnalytics(event: string, properties: AnalyticsProperties = {}) {
  if (!frontendConfig.telemetryEnabled || !frontendConfig.posthogKey) return;
  try {
    posthog.capture(event, sanitizeAnalyticsProperties(properties));
  } catch {
    return;
  }
}
