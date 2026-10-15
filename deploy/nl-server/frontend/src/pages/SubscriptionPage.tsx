import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { SubscriptionData, VpnKey } from '../types'
import { useApp } from '../context'
import { formatDate, formatDateTime, getDaysLeft, getExpiryStatus, normalizeUnixSeconds } from '../utils/time'
import s from './SubscriptionPage.module.css'

interface Props {
  data: SubscriptionData | null
}

const TUNNEL_META = {
  single: {
    icon: '🇳🇱',
    name: 'Нидерланды',
    desc: 'Прямое подключение · VLESS + TLS',
    color: '#40c57b',
  },
  double: {
    icon: '🛡️',
    name: 'Двойной тоннель',
    desc: 'Обход ограничений · VLESS + Reality',
    color: '#57a9ff',
  },
} as const

function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text)
  }

  return new Promise((resolve, reject) => {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (!ok) throw new Error('copy failed')
      resolve()
    } catch (e) {
      reject(e)
    }
  })
}

function KeyCard({ vpnKey, subUrl }: { vpnKey: VpnKey; subUrl: string | null }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState<'vless' | 'sub' | null>(null)

  const meta = TUNNEL_META[vpnKey.tunnel_type]
  const daysLeft = getDaysLeft(vpnKey.expires_at)
  const expiresAt = formatDate(vpnKey.expires_at)
  const expiresAtFull = formatDateTime(vpnKey.expires_at)
  const status = getExpiryStatus(vpnKey.expires_at)

  const statusText =
    status === 'expired'
      ? 'Истекла'
      : daysLeft === 1
      ? '1 день'
      : `${daysLeft} дн.`

  async function handleCopy(text: string, kind: 'vless' | 'sub') {
    try {
      await copyText(text)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      setCopied(kind)
      setTimeout(() => setCopied(null), 1800)
    } catch {
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
    }
  }

  return (
    <div className={s.keyCard} style={{ borderLeftColor: meta.color }}>
      <button className={s.keyHeader} onClick={() => setOpen(v => !v)}>
        <span className={s.keyIcon}>{meta.icon}</span>
        <div className={s.keyInfo}>
          <span className={s.keyName}>{meta.name}</span>
          <span className={s.keyDesc}>{meta.desc}</span>
        </div>
        <div className={s.keyMeta}>
          <span className={s.keyDate}>до {expiresAt}</span>
          <span className={`${s.keyDays} ${s[status]}`}>{statusText}</span>
        </div>
        <span className={s.chevron}>{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className={s.keyDetails}>
          <div className={s.metaLine}>Истекает: {expiresAtFull}</div>
          {vpnKey.vless_link && (
            <div className={s.block}>
              <div className={s.blockLabel}>Конфиг VLESS</div>
              <div className={s.blockText}>{vpnKey.vless_link}</div>
              <button
                className={`${s.copyBtn} ${copied === 'vless' ? s.copied : ''}`}
                onClick={() => handleCopy(vpnKey.vless_link, 'vless')}
              >
                {copied === 'vless' ? 'Скопировано' : 'Копировать конфиг'}
              </button>
            </div>
          )}

          {subUrl && (
            <div className={s.block}>
              <div className={s.blockLabel}>Ссылка подписки (все конфиги)</div>
              <div className={s.blockText}>{subUrl}</div>
              <button
                className={`${s.copyBtn} ${copied === 'sub' ? s.copied : ''}`}
                onClick={() => handleCopy(subUrl, 'sub')}
              >
                {copied === 'sub' ? 'Скопировано' : 'Копировать ссылку'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SubscriptionPage({ data }: Props) {
  const navigate = useNavigate()
  const { refreshSub } = useApp()
  const [refreshing, setRefreshing] = useState(false)

  const keys = data?.keys ?? []
  const subUrl = data?.subscription_url ?? null

  const stats = useMemo(() => {
    const normalized = keys
      .map(k => normalizeUnixSeconds(k.expires_at))
      .filter((x): x is number => x !== null)
      .sort((a, b) => a - b)
    const closest = normalized.length > 0 ? normalized[0] : null
    return {
      total: keys.length,
      closestDate: closest ? formatDate(closest) : '—',
    }
  }, [keys])

  useEffect(() => {
    refreshSub().catch(() => undefined)
  }, [refreshSub])

  async function handleRefresh() {
    setRefreshing(true)
    await refreshSub().catch(() => undefined)
    setRefreshing(false)
  }

  return (
    <div className={s.page}>
      <div className={s.summary}>
        <div>
          <div className={s.summaryTitle}>Ваши подписки</div>
          <div className={s.summaryText}>
            Активных ключей: <b>{stats.total}</b> · Ближайшее окончание: <b>{stats.closestDate}</b>
          </div>
        </div>
        <button className={s.refreshBtn} onClick={handleRefresh} disabled={refreshing}>
          {refreshing ? 'Обновление…' : 'Обновить'}
        </button>
      </div>

      {keys.length === 0 ? (
        <>
          <div className={s.empty}>
            <div className={s.emptyIcon}>🛰️</div>
            <div className={s.emptyTitle}>Нет активных подписок</div>
            <div className={s.emptyText}>Оформите VPN на вкладке «Купить».</div>
          </div>
          <button className={s.buyBtn} onClick={() => navigate('/buy')}>
            Купить VPN
          </button>
        </>
      ) : (
        keys.map(k => (
          <KeyCard key={`${k.email}-${k.tunnel_type}-${k.expires_at}`} vpnKey={k} subUrl={subUrl} />
        ))
      )}

      <div className="section-label">Как добавить в клиент</div>
      <div className={s.hintCard}>
        <div className={s.hintRow}>V2rayN → Подписки → Добавить</div>
        <div className={s.hintRow}>NekoBox → Профили → Новый → URL</div>
        <div className={s.hintRow}>V2rayNG → Подписки → Добавить</div>
        <div className={s.hintRow}>Вставьте ссылку и нажмите «Обновить»</div>
      </div>
    </div>
  )
}

