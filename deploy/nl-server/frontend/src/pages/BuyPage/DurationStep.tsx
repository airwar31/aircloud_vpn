import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import type { TunnelType, Duration } from '../../types'
import { PRICES, DURATION_LABELS, DURATION_BADGES, TUNNEL_LABELS } from '../../constants'
import s from './BuyPage.module.css'

const DURATIONS: Duration[] = ['1_month', '3_months', '12_months']

export default function DurationStep() {
  const navigate = useNavigate()
  const { state } = useLocation() as { state: { plan: TunnelType } }
  const plan = state?.plan

  const [selected, setSelected] = useState<Duration | null>(null)

  if (!plan) {
    navigate('/buy', { replace: true })
    return null
  }

  function choose(dur: Duration) {
    setSelected(dur)
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
  }

  function next() {
    if (!selected) return
    navigate('/buy/pay', { state: { plan, duration: selected } })
  }

  return (
    <>
      <button className={s.backBtn} onClick={() => navigate('/buy')}>
        Назад
      </button>
      <p className="section-label">Срок — {TUNNEL_LABELS[plan]}</p>

      <div className={s.durGrid}>
        {DURATIONS.map(dur => (
          <div
            key={dur}
            className={`${s.durBtn} ${selected === dur ? s.selected : ''}`}
            onClick={() => choose(dur)}
          >
            <div className={s.durPeriod}>{DURATION_LABELS[dur]}</div>
            <div className={s.durPrice}>{PRICES[plan][dur]} ₽</div>
            {DURATION_BADGES[dur] && <div className={s.durBadge}>{DURATION_BADGES[dur]}</div>}
          </div>
        ))}
      </div>

      <button className={`${s.actionBtn} ${s.green}`} onClick={next} disabled={!selected}>
        Продолжить
      </button>
    </>
  )
}

