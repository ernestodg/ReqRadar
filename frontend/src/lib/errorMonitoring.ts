import * as Sentry from "@sentry/react";
import { frontendConfig } from "./config";

const sensitiveKeyParts = ["authorization", "cookie", "token", "secret", "password"];

function sanitize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sanitize);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, item]) => {
      const keyLower = key.toLowerCase();
      if (sensitiveKeyParts.some((part) => keyLower.includes(part)) || ["data", "body", "form", "files"].includes(keyLower)) {
        return [key, "[Filtered]"];
      }
      return [key, sanitize(item)];
    }),
  );
}

export function beforeSend(event: Sentry.ErrorEvent): Sentry.ErrorEvent | null {
  return sanitize(event) as Sentry.ErrorEvent;
}

export function initErrorMonitoring() {
  if (!frontendConfig.telemetryEnabled || !frontendConfig.sentryDsn) return;
  try {
    Sentry.init({
      dsn: frontendConfig.sentryDsn,
      environment: frontendConfig.sentryEnvironment,
      release: frontendConfig.sentryRelease || undefined,
      beforeSend,
    });
  } catch {
    return;
  }
}
