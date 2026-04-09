"use client";

import "@/lib/geraldo-define-client";
import { useLayoutEffect, useRef, type MouseEvent, type ReactNode } from "react";

type Variant = "filled" | "outline" | "ghost";
type Color = "primary" | "secondary" | "danger";
type Size = "sm" | "md" | "lg";

export type GeraldoButtonProps = {
  variant?: Variant;
  color?: Color;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  className?: string;
  children?: ReactNode;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
};

type GeraldoButtonHost = HTMLElement & {
  variant: string;
  color: string;
  size: string;
  loading: boolean;
  disabled: boolean;
  type: string;
};

/**
 * React 19 trata web components principalmente como atributos string; o Lit usa propriedades
 * para :host([variant=…]). Sincronizamos no ref antes do paint. Não repassar variant/color no JSX.
 */
export function GeraldoButton({
  variant = "filled",
  color = "primary",
  size = "md",
  loading = false,
  disabled = false,
  type = "button",
  className,
  children,
  onClick,
}: GeraldoButtonProps) {
  const ref = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const h = el as GeraldoButtonHost;
    h.variant = variant;
    h.color = color;
    h.size = size;
    h.loading = loading;
    h.disabled = disabled;
    h.type = type;
  }, [variant, color, size, loading, disabled, type]);

  return (
    <geraldo-button ref={ref} className={className} onClick={onClick}>
      {children}
    </geraldo-button>
  );
}
