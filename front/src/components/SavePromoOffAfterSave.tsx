"use client";

import { GeraldoButton } from "@/components/GeraldoButton";
import { useEffect, useRef } from "react";

export type SavePromoOffAfterSaveProps = {
  open: boolean;
  onClose: () => void;
  autoCloseMs?: number;
};

/**
 * Pós-salvar com "Ativar Promoção" desligado: não mostra o card de celebração com prévia no app.
 */
export function SavePromoOffAfterSave({
  open,
  onClose,
  autoCloseMs = 6500,
}: SavePromoOffAfterSaveProps) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const t = window.setTimeout(() => {
      onCloseRef.current();
    }, autoCloseMs);
    return () => window.clearTimeout(t);
  }, [open, autoCloseMs]);

  if (!open) return null;

  return (
    <div
      className="xepa-celebration-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="xepa-promo-off-title"
    >
      <div className="xepa-celebration-dim" aria-hidden />
      <div className="xepa-celebration-modal xepa-promo-off-modal">
        <div className="xepa-celebration-mascot xepa-celebration-mascot--quiet" aria-hidden>
          <span className="xepa-celebration-mascot-emoji">✅</span>
        </div>
        <h2 id="xepa-promo-off-title" className="xepa-celebration-title">
          Promoção desativada
        </h2>
        <p className="xepa-celebration-sub xepa-promo-off-sub">
          Suas alterações foram salvas com <strong>Ativar Promoção</strong> desligado: a promoção automática da xepa
          fica fora e os preços no aiqfome voltam ao normal (só preço de lista). Se ainda havia desconto ativo, o robô
          reverte na próxima execução.
        </p>
        <GeraldoButton
          className="xepa-celebration-cta"
          type="button"
          variant="filled"
          color="primary"
          size="lg"
          onClick={() => onClose()}
        >
          Entendi
        </GeraldoButton>
      </div>
    </div>
  );
}
