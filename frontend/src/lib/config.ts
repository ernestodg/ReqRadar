export const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

export const frontendConfig: FrontendConfig = {
  apiUrl,
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL || "",
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY || "",
  authEnabled: !missingSupabaseConfig(import.meta.env.VITE_SUPABASE_URL || "", import.meta.env.VITE_SUPABASE_ANON_KEY || ""),
  authConfigError:
    import.meta.env.PROD && missingSupabaseConfig(import.meta.env.VITE_SUPABASE_URL || "", import.meta.env.VITE_SUPABASE_ANON_KEY || "")
      ? "Production authentication is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY."
      : null,
  isDevelopment: import.meta.env.DEV,
};
