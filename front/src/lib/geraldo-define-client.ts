"use client";

import { defineGeraldoUI } from "@aiqfome-org/geraldo-ui";

/** Registro síncrono no cliente — evita botões sem estilo antes do primeiro paint. */
if (typeof window !== "undefined") {
  defineGeraldoUI();
}
