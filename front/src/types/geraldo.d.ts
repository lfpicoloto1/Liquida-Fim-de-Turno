import type { DetailedHTMLProps, HTMLAttributes } from "react";

type Base = DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement>;

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "geraldo-button": Base & {
        type?: "button" | "submit" | "reset";
        variant?: string;
        color?: string;
        size?: string;
        loading?: boolean;
        disabled?: boolean;
      };
      "geraldo-text": Base & { variant?: string; weight?: string; as?: string };
      "geraldo-badge": Base & { tone?: string };
      "geraldo-card": Base & { radius?: string; elevation?: string };
      "geraldo-text-field": Base & {
        label?: string;
        description?: string;
        error?: string;
        value?: string;
        type?: string;
      };
      "geraldo-checkbox": Base & { checked?: boolean; disabled?: boolean };
      "geraldo-radio-group": Base & { value?: string; name?: string; legend?: string };
      "geraldo-radio": Base & { value?: string; checked?: boolean; name?: string };
      "geraldo-switch": Base & { checked?: boolean; disabled?: boolean };
    }
  }
}

export {};
