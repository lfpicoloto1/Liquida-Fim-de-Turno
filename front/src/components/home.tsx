"use client";

import "@/lib/geraldo-define-client";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Ref,
} from "react";
import Link from "next/link";
import { getDay } from "date-fns";
import { toZonedTime } from "date-fns-tz";
import { isTrustedOrigin } from "@/lib/auth/post-message";
import { GeraldoButton } from "@/components/GeraldoButton";
import { LoginMarketingCarousel } from "@/components/LoginMarketingCarousel";
import { SaveSuccessCelebration } from "@/components/SaveSuccessCelebration";
import {
  brazilTimeZoneSelectOptions,
  DEFAULT_BRAZIL_TIMEZONE,
} from "@/lib/brazil-timezones";

const DAYS: { bit: number; label: string }[] = [
  { bit: 0, label: "Dom" },
  { bit: 1, label: "Seg" },
  { bit: 2, label: "Ter" },
  { bit: 3, label: "Qua" },
  { bit: 4, label: "Qui" },
  { bit: 5, label: "Sex" },
  { bit: 6, label: "Sáb" },
];

const DAY_MOOD_ICONS = ["🥐", "☕", "🌮", "🥗", "🍝", "🍔", "🍕"] as const;

/** Texto único: fluxo do app (hero logado + card de login). Sem “sobre”; “sobras” trocado por liquidação. */
const XEPA_FLOW_DESCRIPTION =
  "Em poucos passos: defina o percentual de desconto da liquidação, escolha em quais categorias do cardápio a promoção vale e, por fim, ajuste com quanto tempo de antecedência ao fechamento da loja as ofertas passam a aparecer no aiqfome. Depois é só salvar.";

function subtractMinutesFromHHMM(hhmm: string, leadMin: number): string {
  const [h, m] = hhmm.split(":").map((x) => Number(x));
  if (!Number.isFinite(h) || !Number.isFinite(m)) return "—";
  let t = h * 60 + m - leadMin;
  while (t < 0) t += 24 * 60;
  const nh = Math.floor(t / 60) % 24;
  const nm = t % 60;
  return `${nh.toString().padStart(2, "0")}:${nm.toString().padStart(2, "0")}`;
}

function XepaRoutineSwitch({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  const ref = useRef<(HTMLElement & { checked?: boolean }) | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (el) el.checked = checked;
  }, [checked]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fn = (e: Event) => {
      const d = (e as CustomEvent<{ checked: boolean }>).detail;
      onCheckedChange(d.checked);
    };
    el.addEventListener("geraldo-change", fn);
    return () => el.removeEventListener("geraldo-change", fn);
  }, [onCheckedChange]);
  return (
    <geraldo-switch ref={ref as Ref<HTMLElement>}>
      Ativar Promoção
    </geraldo-switch>
  );
}

type MeResponse =
  | { authenticated: false }
  | {
      authenticated: true;
      store: {
        id: string;
        externalStoreId: string;
        displayName: string | null;
        timeZone: string;
      };
      /** Só existe após o primeiro "Salvar" — antes disso é `null`. */
      settings: {
        discountPercent: number;
        leadMinutes: number;
        activeWeekdays: number;
        routineEnabled: boolean;
        promoCategoryIds: number[];
      } | null;
      job: {
        lastRunAt: string | null;
        lastError: string | null;
        promoAppliedForDate: string | null;
        lastRevertDate: string | null;
      } | null;
    };

function maskToSelected(mask: number): Set<number> {
  const s = new Set<number>();
  for (const d of DAYS) {
    if (mask & (1 << d.bit)) s.add(d.bit);
  }
  return s;
}

function selectedToMask(selected: Set<number>): number[] {
  return Array.from(selected.values()).sort((a, b) => a - b);
}

type WorkingHoursDayRow = { dowJs: number; label: string; lastClose: string | null };

type MenuCategoryRow = {
  id: number;
  name: string | null;
  culinaryId: number | null;
  status: string | null;
  blockedUntilTomorrow: boolean | null;
  hasDailySale: boolean | null;
};

export function Home() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [discount, setDiscount] = useState(15);
  const [leadUnit, setLeadUnit] = useState<"hours" | "minutes">("minutes");
  const [leadValue, setLeadValue] = useState(60);
  const [days, setDays] = useState<Set<number>>(maskToSelected(62));
  const [routine, setRoutine] = useState(false);
  const [timeZone, setTimeZone] = useState(DEFAULT_BRAZIL_TIMEZONE);
  const [workHours, setWorkHours] = useState<WorkingHoursDayRow[] | null>(null);
  const [workHoursError, setWorkHoursError] = useState<string | null>(null);
  const [menuCategories, setMenuCategories] = useState<MenuCategoryRow[] | null>(null);
  const [menuCategoriesError, setMenuCategoriesError] = useState<string | null>(null);
  const [promoCategories, setPromoCategories] = useState<Set<number>>(new Set());
  const [showSaveCelebration, setShowSaveCelebration] = useState(false);
  const [celebrationDiscount, setCelebrationDiscount] = useState(15);

  const devLoginEnabled = process.env.NEXT_PUBLIC_DEV_LOGIN === "true";

  const timeZoneOptions = useMemo(() => brazilTimeZoneSelectOptions(timeZone), [timeZone]);

  const magaluOAuthBaseMissing = useMemo(() => {
    const clientId = process.env.NEXT_PUBLIC_MAGALU_CLIENT_ID;
    const redirect = process.env.NEXT_PUBLIC_MAGALU_REDIRECT_URI ?? "";
    return !clientId || !redirect;
  }, []);

  const refreshMe = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const apiDebug = process.env.NEXT_PUBLIC_DEBUG_API === "true";
      if (apiDebug && typeof window !== "undefined") {
        console.info("[liquida/api] GET /api/me", {
          browserUrl: `${window.location.origin}/api/me`,
          note: "Same-origin é esperado; o Next reescreve no servidor para API_PROXY_URL.",
        });
      }
      const res = await fetch("/api/me", { credentials: "include" });
      if (apiDebug) {
        console.info("[liquida/api] /api/me response", { status: res.status, ok: res.ok });
      }
      const data = (await res.json()) as MeResponse;
      setMe(data);
      if (data.authenticated) {
        setTimeZone(data.store.timeZone);
        if (data.settings) {
          setDiscount(data.settings.discountPercent);
          setRoutine(data.settings.routineEnabled);
          const lm = data.settings.leadMinutes;
          if (lm % 60 === 0 && lm >= 60) {
            setLeadUnit("hours");
            setLeadValue(lm / 60);
          } else {
            setLeadUnit("minutes");
            setLeadValue(lm);
          }
          setDays(maskToSelected(data.settings.activeWeekdays));
          setPromoCategories(new Set(data.settings.promoCategoryIds ?? []));
        } else {
          setDiscount(15);
          setLeadUnit("minutes");
          setLeadValue(60);
          setDays(maskToSelected(62));
          setRoutine(false);
          setPromoCategories(new Set());
        }
      }
    } catch {
      setError("Não foi possível carregar a sessão.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const closeSaveCelebration = useCallback(() => {
    setShowSaveCelebration(false);
  }, []);

  const storeKey = me && me.authenticated ? me.store.id : null;

  useEffect(() => {
    if (!storeKey) {
      setWorkHours(null);
      setWorkHoursError(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      setWorkHours(null);
      setWorkHoursError(null);
      try {
        const res = await fetch("/api/store/working-hours", { credentials: "include" });
        const j = (await res.json()) as { lastCloseByDow?: WorkingHoursDayRow[]; detail?: string };
        if (cancelled) return;
        if (!res.ok) {
          setWorkHoursError(
            typeof j.detail === "string" ? j.detail : "Não foi possível carregar horários da aiqfome.",
          );
          return;
        }
        setWorkHours(j.lastCloseByDow ?? []);
      } catch {
        if (!cancelled) setWorkHoursError("Não foi possível carregar horários da aiqfome.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storeKey]);

  useEffect(() => {
    if (!storeKey) {
      setMenuCategories(null);
      setMenuCategoriesError(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      setMenuCategories(null);
      setMenuCategoriesError(null);
      try {
        const res = await fetch("/api/store/menu-categories", { credentials: "include" });
        const j = (await res.json()) as { categories?: MenuCategoryRow[]; detail?: string };
        if (cancelled) return;
        if (!res.ok) {
          setMenuCategoriesError(
            typeof j.detail === "string" ? j.detail : "Não foi possível carregar categorias do cardápio.",
          );
          return;
        }
        setMenuCategories(j.categories ?? []);
      } catch {
        if (!cancelled) setMenuCategoriesError("Não foi possível carregar categorias do cardápio.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storeKey]);

  useEffect(() => {
    const onMessage = async (event: MessageEvent) => {
      if (!isTrustedOrigin(event.origin)) return;
      const data = event.data as { type?: string; code?: string; oauthState?: string };
      if (data?.type === "magaluAuthDone") {
        setError(null);
        await refreshMe();
        return;
      }
      if (data?.type !== "authCode" || typeof data.code !== "string") return;
      setError(null);
      const redirectUri = process.env.NEXT_PUBLIC_MAGALU_REDIRECT_URI;
      const res = await fetch("/api/auth/magalu/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          code: data.code,
          redirectUri,
          ...(data.oauthState ? { oauthState: data.oauthState } : {}),
        }),
      });
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { error?: string; detail?: string };
        setError(typeof j.detail === "string" ? j.detail : j.error ?? "Falha ao trocar o code");
        return;
      }
      await refreshMe();
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [refreshMe]);

  const openMagalu = () => {
    if (magaluOAuthBaseMissing) {
      setError("Magalu ID não configurado (NEXT_PUBLIC_MAGALU_CLIENT_ID / REDIRECT_URI).");
      return;
    }
    const clientId = process.env.NEXT_PUBLIC_MAGALU_CLIENT_ID as string;
    const redirect = process.env.NEXT_PUBLIC_MAGALU_REDIRECT_URI ?? "";
    const u = new URL("https://id.magalu.com/login/");
    u.searchParams.set("client_id", clientId);
    u.searchParams.set("redirect_uri", redirect);
    u.searchParams.set("scope", "aqf:store:read aqf:menu:read aqf:menu:create");
    u.searchParams.set("response_type", "code");
    u.searchParams.set("choose_tenants", "true");
    const w = window.open(u.toString(), "magalu_login", "width=600,height=700");
    if (!w) setError("Popup bloqueado — permita popups para este site.");
  };

  const devLogin = async () => {
    setError(null);
    const res = await fetch("/api/auth/magalu/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({}),
    });
    if (!res.ok) {
      const j = (await res.json().catch(() => ({}))) as { error?: string; detail?: string };
      setError(typeof j.detail === "string" ? j.detail : j.error ?? "Falha no login dev");
      return;
    }
    await refreshMe();
  };

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    setMe({ authenticated: false });
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    const started = Date.now();
    const savedDiscount = discount;
    const MIN_CELEBRATION_MS = 480;
    try {
      const res = await fetch("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          discountPercent: discount,
          leadUnit,
          leadValue,
          activeWeekdays: selectedToMask(days),
          routineEnabled: routine,
          timeZone,
          promoCategoryIds: Array.from(promoCategories.values()).sort((a, b) => a - b),
        }),
      });
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { error?: string; detail?: string };
        setError(typeof j.detail === "string" ? j.detail : j.error ?? "Falha ao salvar");
        return;
      }
      await refreshMe();
      const elapsed = Date.now() - started;
      await new Promise((r) => window.setTimeout(r, Math.max(0, MIN_CELEBRATION_MS - elapsed)));
      setCelebrationDiscount(savedDiscount);
      setShowSaveCelebration(true);
    } finally {
      setSaving(false);
    }
  };

  const toggleDay = (bit: number) => {
    setDays((prev) => {
      const n = new Set(prev);
      if (n.has(bit)) n.delete(bit);
      else n.add(bit);
      return n;
    });
  };

  const togglePromoCategory = (categoryId: number) => {
    setPromoCategories((prev) => {
      const n = new Set(prev);
      if (n.has(categoryId)) n.delete(categoryId);
      else n.add(categoryId);
      return n;
    });
  };

  const leadMinutesTotal = useMemo(
    () => (leadUnit === "hours" ? leadValue * 60 : leadValue),
    [leadUnit, leadValue],
  );

  const timelinePct = useMemo(
    () => Math.min(100, (leadMinutesTotal / 240) * 100),
    [leadMinutesTotal],
  );

  const discountMoodEmoji = useMemo(() => {
    if (discount >= 50) return "😅";
    if (discount >= 30) return "😎";
    return "🙂";
  }, [discount]);

  const nextBurnLine = useMemo(() => {
    if (!me || !("authenticated" in me) || !me.authenticated) return "";
    if (!routine) {
      return "Liga o \"Ativar Promoção\" aí em cima pra botar na esteira! 🛒";
    }
    const zNow = toZonedTime(new Date(), timeZone);
    const dow = getDay(zNow);
    for (let i = 0; i < 8; i++) {
      const d = (dow + i) % 7;
      if (!days.has(d)) continue;
      const row = workHours?.find((w) => w.dowJs === d);
      if (!row?.lastClose) continue;
      const start = subtractMinutesFromHHMM(row.lastClose, leadMinutesTotal);
      if (i === 0) return `Próxima queima: hoje às ${start} 🎉`;
      const label = DAYS.find((x) => x.bit === d)?.label ?? "";
      return `Próxima queima: ${label} às ${start} 🎉`;
    }
    return "Marca uns dias da semana aí — senão a xepa não pega fogo! 📅";
  }, [me, routine, timeZone, days, workHours, leadMinutesTotal]);

  const clockDash = useMemo(() => {
    const pct = timelinePct / 100;
    const circumference = 2 * Math.PI * 36;
    const dash = circumference * pct;
    return { circumference, dash };
  }, [timelinePct]);

  if (loading || me === null) {
    return (
      <main className="xepa-dashboard">
        <div className="xepa-dashboard-inner">
          <p className="xepa-loading-msg">Carregando a xepa…</p>
        </div>
      </main>
    );
  }

  if (!me.authenticated) {
    return (
      <main className="xepa-dashboard">
        <div className="xepa-dashboard-inner xepa-login-shell">
          <div className="xepa-toast-stack" aria-live="polite" aria-relevant="additions text">
            {error ? <div className="xepa-toast-fixed xepa-toast-fixed--error">{error}</div> : null}
          </div>

          <section className="xepa-hero xepa-login-hero" aria-label="Boas-vindas">
            <h1 className="xepa-hero-title">Hora da Xepa começa aqui 🔥</h1>
            <p className="xepa-hero-sub xepa-login-hero-tagline">
              Use o Magalu ID (o mesmo da aiqfome) para entrar e configurar tudo no painel abaixo.
            </p>
          </section>

          <geraldo-card className="xepa-widget xepa-login-card" elevation="2" radius="lg">
            <div slot="header" className="xepa-widget-header">
              <span className="xepa-widget-emoji" aria-hidden>
                🔐
              </span>
              <geraldo-text variant="h3-section" weight="medium">
                Bora entrar?
              </geraldo-text>
            </div>
            <div className="xepa-widget-body xepa-widget-body--tight">
              <p className="xepa-hero-sub xepa-login-flow-intro">{XEPA_FLOW_DESCRIPTION}</p>
              <geraldo-text variant="body" weight="regular">
                É o mesmo login Magalu ID que você já usa com a aiqfome. Sem firula: popup, autoriza, pronto.
              </geraldo-text>
              <div className="xepa-login-actions">
                <GeraldoButton type="button" variant="filled" color="primary" size="lg" onClick={openMagalu}>
                  Entrar com Magalu ID
                </GeraldoButton>
                {devLoginEnabled ? (
                  <GeraldoButton type="button" variant="outline" color="primary" size="lg" onClick={devLogin}>
                    Entrar (dev)
                  </GeraldoButton>
                ) : null}
              </div>
              <p className="xepa-login-footnote">
                Popup bloqueado? Libera na barra do navegador e tenta de novo.
              </p>
            </div>
          </geraldo-card>

          <LoginMarketingCarousel />

          <nav className="xepa-legal-footer" aria-label="Documentos legais">
            <Link href="/privacidade">Política de privacidade</Link>
            <span className="xepa-legal-footer-sep" aria-hidden>
              ·
            </span>
            <Link href="/termos">Termos de uso</Link>
          </nav>
        </div>
      </main>
    );
  }

  const job = me.job;

  return (
    <main className="xepa-dashboard">
      <div
        className={`xepa-dashboard-inner${showSaveCelebration ? " xepa-dashboard-inner--save-blur" : ""}`}
        aria-hidden={showSaveCelebration}
      >
        <div className="xepa-toast-stack" aria-live="polite" aria-relevant="additions text">
          {error ? <div className="xepa-toast-fixed xepa-toast-fixed--error">{error}</div> : null}
        </div>

        <section className="xepa-hero" aria-label="Hora da Xepa">
          <div className="xepa-hero-main">
            <div className="xepa-hero-top">
              <div>
                <h1 className="xepa-hero-title">Hora da Xepa! 🔥 Zere sua vitrine no aiqfome</h1>
                <p className="xepa-hero-sub">{XEPA_FLOW_DESCRIPTION}</p>
                <div className="xepa-store-chip">
                  <geraldo-badge tone="primary">{me.store.displayName ?? me.store.externalStoreId}</geraldo-badge>
                </div>
              </div>
              <div className={`xepa-master-switch-wrap${routine ? " xepa-master-on" : ""}`}>
                <XepaRoutineSwitch checked={routine} onCheckedChange={setRoutine} />
              </div>
            </div>
          </div>
        </section>

        {!me.settings ? (
          <p className="xepa-hint-strip">
            Primeira vez aqui? Ajusta os bagulhos abaixo e manda um <strong>Salvar descontos!</strong> pra criar a
            configuração da loja.
          </p>
        ) : null}

        <div className="xepa-card-grid xepa-card-grid--main">
          <div className="xepa-grid-left-stack">
            <geraldo-card className="xepa-widget" elevation="2" radius="lg">
              <div slot="header" className="xepa-widget-header">
                <span className="xepa-widget-emoji" aria-hidden>
                  🔥
                </span>
                <geraldo-text variant="h3-section" weight="medium">
                  O Queimão das Sobras
                </geraldo-text>
              </div>
              <div className="xepa-widget-body">
                <geraldo-text variant="body" weight="medium">
                  Quanto de Desconto? 🤩
                </geraldo-text>
                <p className="muted" style={{ margin: 0 }}>
                  O que tá sobrando hoje?
                </p>
                <div className="xepa-thermo-row">
                  <div className="xepa-thermo-wrap">
                    <input
                      className="xepa-thermo-input"
                      type="range"
                      min={0}
                      max={95}
                      value={discount}
                      onChange={(e) => setDiscount(Number(e.target.value))}
                      aria-label="Percentual de desconto"
                    />
                  </div>
                  <div className="xepa-discount-big">{discount}%</div>
                  <span className="xepa-discount-mood" title="Clima do desconto">
                    {discountMoodEmoji}
                  </span>
                </div>
              </div>
            </geraldo-card>

            <geraldo-card className="xepa-widget xepa-widget--categories" elevation="2" radius="lg">
              <div slot="header" className="xepa-widget-header">
                <geraldo-text variant="h3-section" weight="medium">
                  Categorias do desconto
                </geraldo-text>
              </div>
              <div className="xepa-widget-body xepa-widget-body--tight">
                <p className="muted" style={{ margin: 0, fontSize: "0.95rem" }}>
                  Clique nas opções abaixo onde o desconto deve valer.
                </p>
                {menuCategoriesError ? <p className="error">{menuCategoriesError}</p> : null}
                {menuCategories === null && storeKey && !menuCategoriesError ? (
                  <p className="muted">Carregando cardápio…</p>
                ) : null}
                {menuCategories && menuCategories.length > 0 ? (
                  <div className="xepa-pill-grid xepa-pill-grid--spacious">
                    {menuCategories.map((c) => {
                      const pressed = promoCategories.has(c.id);
                      return (
                        <button
                          key={c.id}
                          type="button"
                          className="xepa-pill"
                          aria-pressed={pressed}
                          onClick={() => togglePromoCategory(c.id)}
                        >
                          {c.name ?? `#${c.id}`}
                          {c.status && c.status !== "AVAILABLE" ? ` (${c.status})` : ""}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
                {menuCategories && menuCategories.length === 0 && !menuCategoriesError ? (
                  <p className="muted">Nenhuma categoria veio da API pra essa loja.</p>
                ) : null}
              </div>
            </geraldo-card>
          </div>

          <geraldo-card className="xepa-widget xepa-grid-schedule-card" elevation="2" radius="lg">
            <div slot="header" className="xepa-widget-header">
              <span className="xepa-widget-emoji" aria-hidden>
                ⏳
              </span>
              <geraldo-text variant="h3-section" weight="medium">
                O Cronômetro da Oportunidade
              </geraldo-text>
            </div>
            <div className="xepa-widget-body">
              <geraldo-text variant="body" weight="medium">
                A Contagem Regressiva
              </geraldo-text>
              <p className="muted" style={{ margin: 0 }}>
                Quanto tempo antes do último fechamento a xepa começa a esquentar?
              </p>
              <div className="xepa-timeline">
                <div className="xepa-timeline-bar" title="Até ~4h de antecedência na régua">
                  <div className="xepa-timeline-fill" style={{ width: `${timelinePct}%` }} />
                </div>
                <p className="xepa-subtle" style={{ margin: 0 }}>
                  {leadMinutesTotal} min antes do &quot;último fechamento&quot; do dia na aiqfome
                </p>
              </div>
              <svg className="xepa-clock-ring" viewBox="0 0 80 80" aria-hidden>
                <defs>
                  <linearGradient id="xepaClockGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#4ade80" />
                    <stop offset="100%" stopColor="#fb923c" />
                  </linearGradient>
                </defs>
                <circle cx="40" cy="40" r="36" fill="none" stroke="#e9d5ff" strokeWidth="8" />
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  fill="none"
                  stroke="url(#xepaClockGrad)"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${clockDash.dash} ${clockDash.circumference}`}
                  transform="rotate(-90 40 40)"
                />
              </svg>
              <div className="xepa-lead-row">
                <label className="stack xepa-lead-field">
                  <geraldo-text variant="body" weight="medium">
                    Unidade
                  </geraldo-text>
                  <select
                    className="xepa-select"
                    value={leadUnit}
                    onChange={(e) => setLeadUnit(e.target.value as "hours" | "minutes")}
                  >
                    <option value="hours">Horas</option>
                    <option value="minutes">Minutos</option>
                  </select>
                </label>
                <label className="stack xepa-lead-field">
                  <geraldo-text variant="body" weight="medium">
                    Valor
                  </geraldo-text>
                  <input
                    className="xepa-native-input"
                    type="number"
                    min={1}
                    value={leadValue}
                    onChange={(e) => setLeadValue(Number(e.target.value))}
                  />
                </label>
              </div>

              <geraldo-text variant="body" weight="medium">
                Dias da semana
              </geraldo-text>
              <div className="xepa-day-row">
                {DAYS.map((d) => (
                  <button
                    key={d.bit}
                    type="button"
                    className="xepa-day-dot"
                    aria-pressed={days.has(d.bit)}
                    onClick={() => toggleDay(d.bit)}
                  >
                    <span className="xepa-day-ico">{DAY_MOOD_ICONS[d.bit]}</span>
                    {d.label}
                  </button>
                ))}
              </div>

              <label className="stack" style={{ gap: "0.35rem" }}>
                <geraldo-text variant="body" weight="medium">
                  Fuso horário (Brasil)
                </geraldo-text>
                <select className="xepa-select" value={timeZone} onChange={(e) => setTimeZone(e.target.value)}>
                  {timeZoneOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <p className="xepa-subtle">Tem que bater com o fuso da loja na aiqfome, senão o dia vira bagunça.</p>
              </label>
            </div>
          </geraldo-card>

          <div className="xepa-grid-right-stack">
            <geraldo-card className="xepa-widget" elevation="2" radius="lg">
              <div slot="header" className="xepa-widget-header">
                <span className="xepa-widget-emoji" aria-hidden>
                  🕐
                </span>
                <geraldo-text variant="h3-section" weight="medium">
                  Horários na aiqfome (só referência)
                </geraldo-text>
              </div>
              <div className="xepa-widget-body xepa-widget-body--tight">
                <p className="muted" style={{ margin: 0, fontSize: "0.9rem" }}>
                  Horário de fechamento que a aiqfome mostra pra cada dia — só pra você conferir se bate com a rotina da
                  loja.
                </p>
                {workHoursError ? <p className="error">{workHoursError}</p> : null}
                {workHours && workHours.length > 0 ? (
                  <>
                    <ul className="xepa-work-list xepa-work-list--columns">
                      {workHours.map((row) => (
                        <li key={row.dowJs}>
                          {row.label}: <strong>{row.lastClose ?? "—"}</strong>
                        </li>
                      ))}
                    </ul>
                    <geraldo-text variant="body" weight="medium">
                      Quando a xepa esquenta (dias que você marcou acima)
                    </geraldo-text>
                    <ul className="xepa-schedule-preview">
                      {DAYS.filter((d) => days.has(d.bit)).map((d) => {
                        const row = workHours.find((w) => w.dowJs === d.bit);
                        if (!row?.lastClose) return null;
                        const at = subtractMinutesFromHHMM(row.lastClose, leadMinutesTotal);
                        return (
                          <li key={d.bit}>
                            {d.label}: começa <strong>{at}</strong> · fecha {row.lastClose}
                          </li>
                        );
                      })}
                    </ul>
                  </>
                ) : storeKey && !workHoursError ? (
                  <p className="muted">Carregando horários…</p>
                ) : null}
              </div>
            </geraldo-card>

            <geraldo-card className="xepa-widget" elevation="2" radius="lg">
              <div slot="header" className="xepa-widget-header">
                <span className="xepa-widget-emoji" aria-hidden>
                  📡
                </span>
                <geraldo-text variant="h3-section" weight="medium">
                  O Radar do Sócio
                </geraldo-text>
              </div>
              <div className="xepa-widget-body xepa-widget-body--tight">
                <div className="xepa-feed">
                  <div className={`xepa-feed-line ${routine ? "xepa-feed-line--go" : "xepa-feed-line--wait"}`}>
                    <span className="xepa-feed-ico">{routine ? "🟢" : "🟡"}</span>
                    <div>
                      <strong>{nextBurnLine}</strong>
                    </div>
                  </div>
                  <div
                    className={`xepa-feed-line ${
                      job?.lastError ? "xepa-feed-line--stop" : job?.lastRunAt ? "xepa-feed-line--go" : "xepa-feed-line--wait"
                    }`}
                  >
                    <span className="xepa-feed-ico">{job?.lastError ? "🔴" : job?.lastRunAt ? "🟢" : "🟡"}</span>
                    <div>
                      {job?.lastError ? (
                        <>
                          <strong>Deu ruim no robô:</strong> {job.lastError}
                        </>
                      ) : job?.lastRunAt ? (
                        <>
                          <strong>Última queima rodou!</strong>{" "}
                          {new Date(job.lastRunAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
                        </>
                      ) : (
                        <>
                          <strong>Agendado / esperando:</strong> ainda sem execução registrada — normal antes da primeira
                          rodada.
                        </>
                      )}
                    </div>
                  </div>
                  <div className="xepa-feed-line xepa-feed-line--go">
                    <span className="xepa-feed-ico">🏷️</span>
                    <div>
                      Promo aplicada (data local): <strong>{job?.promoAppliedForDate ?? "—"}</strong>
                      <br />
                      Última reversão: <strong>{job?.lastRevertDate ?? "—"}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </geraldo-card>
          </div>
        </div>

        <nav className="xepa-legal-footer xepa-legal-footer--dashboard" aria-label="Documentos legais">
          <Link href="/privacidade">Política de privacidade</Link>
          <span className="xepa-legal-footer-sep" aria-hidden>
            ·
          </span>
          <Link href="/termos">Termos de uso</Link>
        </nav>

        <div className="xepa-fab-bar" role="group" aria-label="Salvar ou sair">
          <GeraldoButton type="button" variant="outline" color="primary" size="lg" onClick={logout}>
            Deixa pra lá
          </GeraldoButton>
          <GeraldoButton type="button" variant="filled" color="primary" size="lg" loading={saving} onClick={save}>
            Salvar descontos!
          </GeraldoButton>
        </div>
      </div>
      <SaveSuccessCelebration
        open={showSaveCelebration}
        discountPercent={celebrationDiscount}
        onClose={closeSaveCelebration}
        storeLabel={me.store.displayName ?? me.store.externalStoreId}
      />
    </main>
  );
}
