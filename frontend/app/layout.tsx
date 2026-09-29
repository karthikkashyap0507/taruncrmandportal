import type { Metadata } from "next";
import { Inter, Poppins } from "next/font/google";
import { Footer } from "@/components/shared/footer";
import { Navbar } from "@/components/shared/navbar";
import { Chatbot } from "@/components/shared/chatbot";
import { AuthHydrate } from "@/components/auth-hydrate";
import { Providers } from "@/components/providers";
import { RoutePrefetcher } from "@/components/shared/route-prefetcher";
import { SITE } from "@/lib/constants";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: {
    default: `${SITE.name} — ${SITE.tagline}`,
    template: `%s | ${SITE.name}`,
  },
  description: SITE.description,
  openGraph: {
    title: SITE.name,
    description: SITE.description,
    type: "website",
    url: SITE.url,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${poppins.variable} min-h-screen font-sans antialiased`}>
        <Providers>
          <AuthHydrate />
          <RoutePrefetcher />
          <Navbar />
          <main className="min-h-screen pt-16">{children}</main>
          <Footer />
          <Chatbot />
        </Providers>
      </body>
    </html>
  );
}
