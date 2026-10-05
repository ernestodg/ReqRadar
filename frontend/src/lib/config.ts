const configuredApiUrl = import.meta.env.VITE_API_URL || "";
export const apiUrl = configuredApiUrl || (import.meta.env.DEV ? "http://localhost:8000" : "");

export type FrontendConfig = {
  apiUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  authEnabled: boolean;
  authConfigError: string | null;
  isDevelopment: boolean;
};

function missingSupabaseConfig(url: string, anonKey: string) {
  return !url || !anonKey;
}

function apiConfigError() {
  if (import.meta.env.PROD && !configuredApiUrl) {
    return "Production API is not configured. Set VITE_API_URL.";
  }
  return null;
}

function authConfigError() {
  if (import.meta.env.PROD && missingSupabaseConfig(import.meta.env.VITE_SUPABASE_URL || "", import.meta.env.VITE_SUPABASE_ANON_KEY || "")) {
    return "Production authentication is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.";
  }
  return null;
}

export const frontendConfig: FrontendConfig = {
  apiUrl,
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL || "",
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY || "",
  authEnabled: !missingSupabaseConfig(import.meta.env.VITE_SUPABASE_URL || "", import.meta.env.VITE_SUPABASE_ANON_KEY || ""),
  authConfigError: apiConfigError() || authConfigError(),
  isDevelopment: import.meta.env.DEV,
};
