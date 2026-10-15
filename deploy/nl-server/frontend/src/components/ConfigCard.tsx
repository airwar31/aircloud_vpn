import type { VpnKey } from '../types'
import { formatDate, getDaysLeft, getExpiryStatus } from '../utils/time'
import s from './ConfigCard.module.css'

const TUNNEL_META = {
  single: { icon: '🇳🇱', name: 'Нидерланды', desc: 'Прямое · VLESS + TLS', color: 'var(--accent)' },
  double: { icon: '🛡️', name: 'Двойной', desc: 'Обход · VLESS + Reality', color: 'var(--blue)' },
}

interface Props {
  vpnKey: VpnKey
}

export default function ConfigCard({ vpnKey }: Props) {
  const meta = TUNNEL_META[vpnKey.tunnel_type]
  const days = getDaysLeft(vpnKey.expires_at)
  const expires = formatDate(vpnKey.expires_at)
  const status = getExpiryStatus(vpnKey.expires_at)
  const daysText = status === 'expired' ? 'Истекла' : `${days} дн.`

  const daysClass = status === 'danger' || status === 'expired' ? s.bad : status === 'warning' ? s.warn : s.ok

  return (
    <div className={s.card} style={{ borderLeftColor: meta.color }}>
      <div className={s.head}>
        <span className={s.icon}>{meta.icon}</span>
        <div>
          <div className={s.name}>{meta.name}</div>
          <div className={s.desc}>{meta.desc}</div>
        </div>
      </div>
      <div className={s.foot}>
        <span className={s.expire}>🗓 {expires}</span>
        <span className={`${s.days} ${daysClass}`}>⏳ {daysText}</span>
      </div>
    </div>
  )
}

