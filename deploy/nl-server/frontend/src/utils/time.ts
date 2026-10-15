export type DateInput = number | string | null | undefined

export function normalizeUnixSeconds(value: DateInput): number | null {
  if (value === null || value === undefined || value === '') {
    return null
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    if (value > 1e12) return value / 1000
    return value
  }

  const text = String(value).trim()
  if (!text) return null

  const numeric = Number(text)
  if (!Number.isNaN(numeric) && Number.isFinite(numeric)) {
    if (numeric > 1e12) return numeric / 1000
    return numeric
  }

  const parsed = Date.parse(text)
  if (!Number.isNaN(parsed)) {
    return parsed / 1000
  }

  return null
}

export function formatDate(value: DateInput, locale = 'ru-RU'): string {
  const ts = normalizeUnixSeconds(value)
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleDateString(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatDateTime(value: DateInput, locale = 'ru-RU'): string {
  const ts = normalizeUnixSeconds(value)
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getDaysLeft(value: DateInput): number {
  const ts = normalizeUnixSeconds(value)
  if (!ts) return 0
  const diff = ts - Date.now() / 1000
  if (diff <= 0) return 0
  return Math.ceil(diff / 86400)
}

export function getExpiryStatus(value: DateInput): 'expired' | 'danger' | 'warning' | 'ok' {
  const days = getDaysLeft(value)
  if (days <= 0) return 'expired'
  if (days <= 3) return 'danger'
  if (days <= 14) return 'warning'
  return 'ok'
}
