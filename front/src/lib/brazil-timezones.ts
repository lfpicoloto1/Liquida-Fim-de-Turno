/**
 * Zonas IANA usadas no território brasileiro (relogio oficial por região).
 * Ordem: mais comum primeiro, depois por offset aproximado.
 */
export const BRAZIL_TIMEZONES: readonly { value: string; label: string }[] = [
  {
    value: "America/Sao_Paulo",
    label: "Horário de Brasília (UTC−3) — SP, RJ, MG, RS, PR, SC, ES, GO, DF e maior parte do país",
  },
  { value: "America/Fortaleza", label: "Fortaleza (UTC−3) — CE, RN, PB, PI, MA" },
  { value: "America/Recife", label: "Recife (UTC−3) — PE" },
  { value: "America/Maceio", label: "Maceió (UTC−3) — AL, SE" },
  { value: "America/Bahia", label: "Salvador / Bahia (UTC−3)" },
  { value: "America/Belem", label: "Belém (UTC−3) — PA (leste), Amapá" },
  { value: "America/Santarem", label: "Santarém (UTC−3) — PA (oeste)" },
  { value: "America/Araguaina", label: "Palmas (UTC−3) — TO" },
  { value: "America/Cuiaba", label: "Cuiabá (UTC−4) — MT" },
  { value: "America/Campo_Grande", label: "Campo Grande (UTC−4) — MS" },
  { value: "America/Manaus", label: "Manaus (UTC−4) — AM (maior parte)" },
  { value: "America/Boa_Vista", label: "Boa Vista (UTC−4) — RR" },
  { value: "America/Porto_Velho", label: "Porto Velho (UTC−4) — RO" },
  { value: "America/Eirunepe", label: "Eirunepé e região (UTC−5) — AM (sudoeste)" },
  { value: "America/Rio_Branco", label: "Rio Branco (UTC−5) — AC" },
  { value: "America/Noronha", label: "Fernando de Noronha (UTC−2)" },
] as const;

export const DEFAULT_BRAZIL_TIMEZONE = "America/Sao_Paulo";

const KNOWN = new Set(BRAZIL_TIMEZONES.map((t) => t.value));

export function isBrazilTimeZone(value: string): boolean {
  return KNOWN.has(value);
}

/** Opções do select; se o valor atual não for um fuso BR conhecido, inclui uma linha no topo. */
export function brazilTimeZoneSelectOptions(currentValue: string): { value: string; label: string }[] {
  if (isBrazilTimeZone(currentValue)) {
    return [...BRAZIL_TIMEZONES];
  }
  return [
    {
      value: currentValue,
      label: `${currentValue} (valor atual — escolha um fuso do Brasil abaixo)`,
    },
    ...BRAZIL_TIMEZONES,
  ];
}
