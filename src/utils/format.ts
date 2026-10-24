const INDIA_CURRENCY = 'en-IN';

export function formatINR(value: number, withDecimals = false): string {
  return new Intl.NumberFormat(INDIA_CURRENCY, {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: withDecimals ? 2 : 0,
    maximumFractionDigits: withDecimals ? 2 : 0,
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
