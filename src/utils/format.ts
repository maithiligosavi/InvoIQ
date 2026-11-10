const INDIA_CURRENCY = 'en-IN';

export function formatINR(value: number, withDecimals?: boolean): string {
  const hasFraction = value % 1 !== 0;
  const showDecimals = withDecimals !== undefined ? withDecimals : hasFraction;
  return new Intl.NumberFormat(INDIA_CURRENCY, {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat(INDIA_CURRENCY).format(value);
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}
