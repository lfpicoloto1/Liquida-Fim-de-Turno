"use client";

import { useCallback, useEffect, useState } from "react";

const AUTO_MS = 5500;

const SLIDES = [
  {
    src: "/login-carousel/slide-1-fim-de-turno.png",
    alt: "Campanha Fim de Turno no aiqfome: descontos automáticos e destaque no app.",
  },
  {
    src: "/login-carousel/slide-2-painel.png",
    alt: "Painel Liquida: configure desconto, categorias e horários da xepa.",
  },
  {
    src: "/login-carousel/slide-3-sucesso.png",
    alt: "Confirmação após salvar: prévia de como a oferta aparece no app.",
  },
] as const;

export function LoginMarketingCarousel() {
  const [index, setIndex] = useState(0);

  const go = useCallback((n: number) => {
    setIndex(((n % SLIDES.length) + SLIDES.length) % SLIDES.length);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return undefined;
    }
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % SLIDES.length);
    }, AUTO_MS);
    return () => window.clearInterval(id);
  }, []);

  return (
    <section
      className="xepa-login-carousel"
      aria-roledescription="carrossel"
      aria-label="Imagens do produto Liquida Fim de Turno"
    >
      <div className="xepa-login-carousel-frame">
        {SLIDES.map((slide, i) => (
          <div
            key={slide.src}
            className={`xepa-login-carousel-slide${i === index ? " xepa-login-carousel-slide--active" : ""}`}
            aria-hidden={i !== index}
          >
            <img src={slide.src} alt={slide.alt} loading={i === 0 ? "eager" : "lazy"} decoding="async" />
          </div>
        ))}
      </div>
      <div className="xepa-login-carousel-dots" role="tablist" aria-label="Selecionar imagem">
        {SLIDES.map((_, i) => (
          <button
            key={i}
            type="button"
            role="tab"
            aria-selected={i === index}
            aria-label={`Imagem ${i + 1} de ${SLIDES.length}`}
            className={`xepa-login-carousel-dot${i === index ? " xepa-login-carousel-dot--active" : ""}`}
            onClick={() => go(i)}
          />
        ))}
      </div>
    </section>
  );
}
