import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { ensureCsrfCookie } from "@/api/queries";
import { AuthProvider } from "@/auth/AuthContext";
import { Toaster } from "@/components/ui/toast";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

/** Django sets the CSRF cookie on first contact; do it before any POST. */
function CsrfBootstrap() {
  useEffect(() => {
    void ensureCsrfCookie().catch(() => {
      // The API being unreachable is surfaced by the pages themselves.
    });
  }, []);

  return null;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <CsrfBootstrap />
          <App />
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
