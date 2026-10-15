import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import type { TunnelType, Duration, PaymentMethod } from '../../types'
import { PRICES, DURATION_LABELS, TUNNEL_LABELS, rublesToStars } from '../../constants'
import { createPayment } from '../../api'
import { useApp } from '../../context'
import s from './BuyPage.module.css'

interface LocationState {
  plan: TunnelType
  duration: Duration
}

const METHODS: { id: PaymentMethod; icon: string; name: string; desc: string }[] = [
  { id: 'stars', icon: '⭐', name: 'Telegram Stars', desc: 'Встроенная оплата · Моментально' },
  { id: 'yookassa', icon: '💳', name: 'YooKassa', desc: 'Карты · Электронные кошельки' },
]

export default function PaymentStep() {
  const navigate = useNavigate()
  const { state } = useLocation() as { state: LocationState }
  const { plan, duration } = state ?? {}
  const { userId } = useApp()

  const [method, setMethod] = useState<PaymentMethod | null>(null)
  const [loading, setLoading] = useState(false)

  if (!plan || !duration) {
    navigate('/buy', { replace: true })
    return null
  }

  const price = PRICES[plan][duration]
  const stars = rublesToStars(price)

  function choose(m: PaymentMethod) {
    setMethod(m)
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
  }

  async function pay() {
    if (!method || !userId) return
    const tg = window.Telegram?.WebApp
    tg?.HapticFeedback?.impactOccurred('medium')
    setLoading(true)

    try {
      const result = await createPayment({ user_id: userId, tunnel_type: plan, duration, method })

      if (result.type === 'invoice' && result.invoice_link) {
        tg?.openInvoice(result.invoice_link, status => {
          navigate('/buy/result', {
            state: { resultType: status === 'paid' ? 'success_stars' : 'cancelled' },
          })
        })
        setLoading(false)
        return
      }

      if (result.type === 'url' && result.url) {
        tg?.openLink(result.url)
        navigate('/buy/result', { state: { resultType: 'yookassa_pending' } })
        return
      }

      navigate('/buy/result', { state: { resultType: 'failed' } })
    } catch {
      navigate('/buy/result', { state: { resultType: 'error' } })
    } finally {
      setLoading(false)
    }
  }

  const payLabel = loading
    ? 'Создаём платёж…'
    : method === 'stars'
    ? `Оплатить ${stars} Stars`
    : method === 'yookassa'
    ? `Оплатить ${price} ₽`
    : 'Оплатить'

  return (
    <>
      <button className={s.backBtn} onClick={() => navigate('/buy/dur', { state: { plan } })}>
        Назад
      </button>

      <p className="section-label">Сводка</p>
      <div className={s.summaryCard}>
        <div className={s.summaryRow}>
          <span>Тариф</span>
          <span className={s.summaryVal}>{TUNNEL_LABELS[plan]}</span>
        </div>
        <div className={s.summaryRow}>
          <span>Срок</span>
          <span className={s.summaryVal}>{DURATION_LABELS[duration]}</span>
        </div>
        <div className={`${s.summaryRow} ${s.summaryTotal}`}>
          <span>Стоимость</span>
          <span className={s.summaryVal}>
            {price} ₽ / {stars} Stars
          </span>
        </div>
      </div>

      <p className="section-label">Способ оплаты</p>
      {METHODS.map(m => (
        <div
          key={m.id}
          className={`${s.payMethod} ${method === m.id ? s.selected : ''}`}
          onClick={() => choose(m.id)}
        >
          <span className={s.payMethodIcon}>{m.icon}</span>
          <div>
            <div className={s.payMethodName}>{m.name}</div>
            <div className={s.payMethodDesc}>{m.desc}</div>
          </div>
        </div>
      ))}

      <button className={`${s.actionBtn} ${s.green}`} onClick={pay} disabled={!method || loading}>
        {payLabel}
      </button>
    </>
  )
}

