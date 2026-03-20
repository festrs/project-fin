import type { Money } from "../types";

const CURRENCY_CONFIG: Record<string, { symbol: string; spacing: string; thousandsSep: string; decimalSep: string }> = {
  USD: { symbol: "$", spacing: "", thousandsSep: ",", decimalSep: "." },
  BRL: { symbol: "R$", spacing: " ", thousandsSep: ".", decimalSep: "," },
  EUR: { symbol: "\u20AC", spacing: "", thousandsSep: ".", decimalSep: "," },
};

export function formatMoney(money: Money | null | undefined, decimals: number = 2): string {
  if (!money) return "\u2014";
  const config = CURRENCY_CONFIG[money.currency] ?? { symbol: money.currency, spacing: "", thousandsSep: ",", decimalSep: "." };
  const num = parseFloat(money.amount);
  const isNegative = num < 0;
  const abs = Math.abs(num);
  const [intPart, fracPart] = abs.toFixed(decimals).split(".");
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, config.thousandsSep);
  const result = `${config.symbol}${config.spacing}${formatted}${config.decimalSep}${fracPart}`;
  return isNegative ? `-${result}` : result;
}

export function moneyToNumber(money: Money | null | undefined): number {
  if (!money) return 0;
  return parseFloat(money.amount);
}
