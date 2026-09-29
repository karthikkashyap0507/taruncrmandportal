"use client";
import "./globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useState } from "react";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30000, retry: 1 } },
  }));

  return (
    <html lang="en">
      <head>
        <title>JobsNexGen CRM</title>
        <meta name="description" content="JobsNexGen CRM Platform" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: { borderRadius: "8px", fontSize: "14px" },
              success: { iconTheme: { primary: "#7c3aed", secondary: "#fff" } },
            }}
          />
        </QueryClientProvider>
      </body>
    </html>
  );
}
