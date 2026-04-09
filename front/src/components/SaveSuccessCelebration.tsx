"use client";

import { useEffect, useRef, useState } from "react";

const PREVIEW_BASE_PRICE = 35;

function formatBrl(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

type SampleItem = { name: string; categoryName: string | null };

export type SaveSuccessCelebrationProps = {
  open: boolean;
  discountPercent: number;
  onClose: () => void;
  /** Nome da loja no mock (como no app). */
  storeLabel?: string | null;
  /** Fechamento automático em ms (default ~8,2s). */
  autoCloseMs?: number;
};

export function SaveSuccessCelebration({
  open,
  discountPercent,
  onClose,
  storeLabel,
  autoCloseMs = 8200,
}: SaveSuccessCelebrationProps) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const [sampleItem, setSampleItem] = useState<SampleItem | null>(null);

  useEffect(() => {
    if (!open) {
      setSampleItem(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/store/menu-sample-item", { credentials: "include" });
        if (!res.ok || cancelled) return;
        const j = (await res.json()) as { name?: string | null; categoryName?: string | null };
        if (cancelled) return;
        if (typeof j.name === "string" && j.name.trim()) {
          setSampleItem({
            name: j.name.trim(),
            categoryName: typeof j.categoryName === "string" && j.categoryName.trim() ? j.categoryName.trim() : null,
          });
        }
      } catch {
        /* fallback abaixo */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

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
    let cancelled = false;
    const reduceMotion =
      typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    void import("canvas-confetti").then((mod) => {
      if (cancelled || reduceMotion) return;
      const confetti = mod.default;
      confetti({
        particleCount: 110,
        spread: 72,
        startVelocity: 38,
        origin: { y: 0.52 },
        scalar: 0.95,
        ticks: 280,
      });
      window.setTimeout(() => {
        if (cancelled) return;
        confetti({ particleCount: 45, angle: 55, spread: 50, origin: { x: 0, y: 0.62 } });
        confetti({ particleCount: 45, angle: 125, spread: 50, origin: { x: 1, y: 0.62 } });
      }, 240);
    });
    const t = window.setTimeout(() => {
      onCloseRef.current();
    }, autoCloseMs);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [open, autoCloseMs]);

  if (!open) return null;

  const pct = Math.min(95, Math.max(0, Math.round(discountPercent)));
  const newPrice = Math.round(PREVIEW_BASE_PRICE * (100 - pct)) / 100;
  const storeName = (storeLabel ?? "Sua loja").trim() || "Sua loja";

  const categoryHeading = sampleItem?.categoryName ?? "Fim de expediente";
  const itemTitle = sampleItem?.name ?? "Um item do seu cardápio";

  return (
    <div
      className="xepa-celebration-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="xepa-celebration-title"
    >
      <div className="xepa-celebration-dim" aria-hidden />
      <div className="xepa-celebration-modal">
        <div className="xepa-celebration-mascot" aria-hidden>
          <span className="xepa-celebration-mascot-emoji">🥟</span>
        </div>
        <h2 id="xepa-celebration-title" className="xepa-celebration-title">
          Aooo, sucesso! A Xepa tá on! 🎉
        </h2>
        <p className="xepa-celebration-sub">
          Tudo salvo. Prepara a embalagem que os pedidos vão chegar!
        </p>

        <div className="xepa-celebration-preview-label">Prévia no app (estilo aiqfome)</div>

        <div className="xepa-aiq-preview-shell">
          <div className="xepa-aiq-preview-store-card">
            <div className="xepa-aiq-preview-store-row">
              <div className="xepa-aiq-preview-logo" aria-hidden>
                <span>🍔</span>
              </div>
              <div className="xepa-aiq-preview-store-main">
                <div className="xepa-aiq-preview-store-name">{storeName}</div>
                <div className="xepa-aiq-preview-delivery">
                  <span className="xepa-aiq-preview-moto" aria-hidden>
                    🛵
                  </span>
                  <span className="xepa-aiq-preview-linkish">ver taxas ›</span>
                  <span className="xepa-aiq-preview-time">hoje, 40 – 60 min</span>
                </div>
              </div>
              <span className="xepa-aiq-preview-details">detalhes ›</span>
            </div>
          </div>

          <div className="xepa-aiq-preview-search" aria-hidden>
            <span className="xepa-aiq-preview-search-ico">🔍</span>
            <span className="xepa-aiq-preview-search-ph">busque por item ou categoria</span>
          </div>

          <div className="xepa-aiq-preview-cat-row">
            <span className="xepa-aiq-preview-cat-icon" aria-hidden>
              %
            </span>
            <span className="xepa-aiq-preview-cat-title">{categoryHeading}</span>
          </div>
          <p className="xepa-aiq-preview-cat-desc">Desconto automático na reta final do dia.</p>

          <div className="xepa-aiq-preview-divider" aria-hidden />

          <div className="xepa-aiq-preview-item">
            <div className="xepa-aiq-preview-thumb-wrap xepa-aiq-preview-thumb-wrap--placeholder" aria-hidden>
              <span className="xepa-aiq-preview-thumb-ph-ico">🍽️</span>
            </div>
            <div className="xepa-aiq-preview-item-body">
              <div className="xepa-aiq-preview-item-title">
                <span className="xepa-aiq-preview-spark" aria-hidden>
                  ✦
                </span>
                <span className="xepa-aiq-preview-item-name-text">{itemTitle}</span>
              </div>
              <div className="xepa-aiq-preview-highlight-row">
                <span className="xepa-aiq-preview-price-big">{formatBrl(newPrice)}</span>
                <span className="xepa-aiq-preview-pct-pill">-{pct}%</span>
                <span className="xepa-aiq-preview-was">{formatBrl(PREVIEW_BASE_PRICE)}</span>
              </div>
              <div className="xepa-aiq-preview-depor">
                <span className="xepa-aiq-preview-de">de {formatBrl(PREVIEW_BASE_PRICE)}</span>
                <span className="xepa-aiq-preview-por">
                  por <strong>{formatBrl(newPrice)}</strong>
                </span>
              </div>
              <p className="xepa-aiq-preview-item-desc">
                <strong>Só um exemplo visual:</strong> o nome acima pode ser um item aleatório do seu cardápio para você
                ver o estilo da oferta. O <strong>mesmo desconto vale para todos os itens</strong> das categorias que
                você marcou — no app aiqfome cada produto mostra o <strong>preço real</strong> dele com a promo.
              </p>
            </div>
          </div>
        </div>

        <geraldo-button
          className="xepa-celebration-cta"
          type="button"
          variant="filled"
          color="secondary"
          size="lg"
          onClick={() => onClose()}
        >
          Voltar pro painel
        </geraldo-button>
      </div>
    </div>
  );
}
