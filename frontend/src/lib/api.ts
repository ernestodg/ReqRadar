import { frontendConfig } from "./config";
import { supabase } from "./supabase";

export class ApiAuthError extends Error {
  constructor(message = "Your session expired. Please sign in again.") {
    super(message);
    this.name = "ApiAuthError";
  }
}

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) {
    return null;
  }
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw new ApiAuthError(error.message);
  }
  return data.session?.access_token ?? null;
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new globalThis.Headers(options.headers);
  if (!headers.has("content-type") && options.body) {
    headers.set("content-type", "application/json");
  }
  const accessToken = await getAccessToken();
  if (accessToken) {
    headers.set("authorization", `Bearer ${accessToken}`);
  }
  const response = await fetch(`${frontendConfig.apiUrl}${path}`, { ...options, headers });
  if (response.status === 401) {
    await supabase?.auth.signOut();
    throw new ApiAuthError();
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: response.statusText } }));
    throw new Error(error.error?.message || "Radar could not complete the request.");
  }
  return response.json();
}
