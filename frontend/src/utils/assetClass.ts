const FIXED_INCOME_TERMS = ["renda fixa", "fixed income"];

export function isFixedIncomeClass(className: string): boolean {
  const lower = className.toLowerCase();
  return FIXED_INCOME_TERMS.some((term) => lower.includes(term));
}
