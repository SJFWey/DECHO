"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

const ApiContext = createContext<{ baseUrl: string }>({
  baseUrl: "http://127.0.0.1:8000/api",
});

export const useApi = () => useContext(ApiContext);

export function ApiProvider({ children }: { children: React.ReactNode }) {
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8000/api");

  useEffect(() => {
    // In a real Tauri app, we might read this from a window variable injected by Rust
    // or fetch it from a known local endpoint.
    // For now, we'll check if a global variable exists.
    if (typeof window !== "undefined" && (window as any).__TAURI_PY_PORT__) {
      setBaseUrl(`http://127.0.0.1:${(window as any).__TAURI_PY_PORT__}/api`);
    }
  }, []);

  // Also update the global/local storage so non-react code (like api.ts) can access it if needed,
  // although we will try to make api.ts dynamic.
  useEffect(() => {
    if (typeof window !== "undefined") {
        localStorage.setItem("api_base_url", baseUrl);
    }
  }, [baseUrl]);

  return (
    <ApiContext.Provider value={{ baseUrl }}>
      {children}
    </ApiContext.Provider>
  );
}
