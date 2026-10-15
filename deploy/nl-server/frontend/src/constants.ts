import type { TunnelType, Duration } from './types'

export const PRICES: Record<TunnelType, Record<Duration, number>> = {
  single: { '1_month': 150, '3_months': 400, '12_months': 1200 },
  double: { '1_month': 250, '3_months': 650, '12_months': 2200 },
}

export const DURATION_LABELS: Record<Duration, string> = {
  '1_month': '1 месяц',
  '3_months': '3 месяца',
  '12_months': '12 месяцев',
}

export const DURATION_BADGES: Record<Duration, string> = {
  '1_month': '',
  '3_months': 'Скидка',
  '12_months': 'Выгодно',
}

export const TUNNEL_LABELS: Record<TunnelType, string> = {
  single: '🇳🇱 Нидерланды',
  double: '🛡️ Двойной тоннель',
}

export const STARS_RATE = 0.8 // rubles -> Stars

export function rublesToStars(rubles: number): number {
  return Math.max(Math.floor(rubles * STARS_RATE), 1)
}

