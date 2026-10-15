import { useNavigate } from 'react-router-dom'
import type { TunnelType } from '../../types'
import s from './BuyPage.module.css'

const PLANS: { type: TunnelType; icon: string; name: string; tagline: string; price: string }[] = [
  {
    type: 'single',
    icon: '🇳🇱',
    name: 'Нидерланды',
    tagline: 'Прямое подключение · VLESS + TLS',
    price: 'от 150 ₽/мес',
  },
  {
    type: 'double',
    icon: '🛡️',
    name: 'Двойной тоннель',
    tagline: 'Обход ограничений · VLESS + Reality',
    price: 'от 250 ₽/мес',
  },
]

export default function PlanStep() {
  const navigate = useNavigate()

  function select(type: TunnelType) {
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
    navigate('/buy/dur', { state: { plan: type } })
  }

  return (
    <>
      <p className="section-label">Выберите тариф</p>
      {PLANS.map(p => (
        <div key={p.type} className={s.planCard} onClick={() => select(p.type)}>
          <div className={s.planHead}>
            <span className={s.planIcon}>{p.icon}</span>
            <div>
              <div className={s.planName}>{p.name}</div>
              <div className={s.planTagline}>{p.tagline}</div>
              <div className={s.planPrice}>{p.price}</div>
            </div>
          </div>
        </div>
      ))}
    </>
  )
}

