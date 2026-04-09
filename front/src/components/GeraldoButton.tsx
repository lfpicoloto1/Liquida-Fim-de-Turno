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
 * O estilo do `geraldo-button` usa `:host([variant=…])` etc. (seletores de atributo no host).
 * No React 19, `variant` / `color` / `size` viram atribuição de *propriedade* no custom element
 * (`key in domElement`), e o Lit não reflete essas props — os atributos somem e o botão fica “cru”.
 * Forçamos os atributos no layout effect (antes do paint) para o shadow CSS bater.
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
    el.setAttribute("variant", variant);
    el.setAttribute("color", color);
    el.setAttribute("size", size);
    const h = el as GeraldoButtonHost;
    h.loading = loading;
    h.disabled = disabled;
    h.type = type;
  }, [variant, color, size, loading, disabled, type]);

  return (
    <geraldo-button
      ref={ref}
      className={className}
      variant={variant}
      color={color}
      size={size}
      loading={loading}
      disabled={disabled}
      type={type}
      onClick={onClick}
    >
      {children}
    </geraldo-button>
  );
}
