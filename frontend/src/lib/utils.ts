import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
export const number = (value: number | null | undefined) =>
  value == null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)
export const percent = (value: number) => `${(value * 100).toFixed(1)}%`
