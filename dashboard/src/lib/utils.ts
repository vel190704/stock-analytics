import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import numeral from 'numeral';

// ---------------------------------------------------------------------------
// Tailwind class merging
// ---------------------------------------------------------------------------

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// ---------------------------------------------------------------------------
// Price formatting
// ---------------------------------------------------------------------------

/**
 * Format a price to 2 decimal places with $ prefix.
 * e.g. 182.5 → "$182.50"
 */
export function formatPrice(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  return `$${numeral(value).format('0,0.00')}`;
}

/**
 * Format a percentage change with sign and 2 decimal places.
 * e.g. 1.384 → "+1.38%"   -0.5 → "-0.50%"
 */
export function formatPct(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${numeral(value).format('0.00')}%`;
}

/**
 * Format volume in abbreviated form.
 * e.g. 2150000 → "2.15M"   850000 → "850K"
 */
export function formatVolume(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  if (value >= 1_000_000_000) return numeral(value).format('0.00b').toUpperCase();
  if (value >= 1_000_000) return numeral(value).format('0.00a').toUpperCase();
  if (value >= 1_000) return numeral(value).format('0.0a').toUpperCase();
  return String(value);
}

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

/**
 * Returns a Tailwind text colour class for a pct change value.
 */
export function priceColour(value: number | null | undefined): string {
  if (value == null) return 'text-text-muted';
  if (value > 0) return 'text-gain';
  if (value < 0) return 'text-loss';
  return 'text-text-muted';
}

/**
 * Returns a hex colour string for use in Recharts (non-Tailwind contexts).
 */
export function priceHex(value: number | null | undefined): string {
  if (value == null) return '#7d8590';
  if (value > 0) return '#3fb950';
  if (value < 0) return '#f85149';
  return '#7d8590';
}

// ---------------------------------------------------------------------------
// Misc
// ---------------------------------------------------------------------------

/** Generate a short random ID (not UUID-grade, just for list keys). */
export function shortId(): string {
  return Math.random().toString(36).slice(2, 10);
}
