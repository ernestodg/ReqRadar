import { createClient } from "@supabase/supabase-js";
import { frontendConfig } from "./config";

export const supabase = frontendConfig.authEnabled
  ? createClient(frontendConfig.supabaseUrl, frontendConfig.supabaseAnonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    })
  : null;
