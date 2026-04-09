import type { Metadata } from "next";
import { Ubuntu } from "next/font/google";
import { GeraldoRegister } from "@/components/geraldo-register";
import "./globals.css";

const ubuntu = Ubuntu({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  variable: "--font-ubuntu",
});

export const metadata: Metadata = {
  title: "Liquida Fim de Turno",
  description: "Promoção automática antes do fechamento (aiqfome)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={ubuntu.variable}>
      <body>
        <GeraldoRegister />
        {children}
      </body>
    </html>
  );
}
