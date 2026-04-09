"use client";

import { useEffect } from "react";

export function GeraldoRegister() {
  useEffect(() => {
    void import("@aiqfome-org/geraldo-ui").then((m) => {
      if (typeof m.defineGeraldoUI === "function") {
        m.defineGeraldoUI();
      }
    });
  }, []);
  return null;
}
