import { useNavigate, useLocation } from 'react-router-dom'
import s from './TabBar.module.css'

const TABS = [
  { path: '/subscription', icon: '🛰️', label: 'Подписка' },
  { path: '/buy', icon: '🛒', label: 'Купить' },
  { path: '/help', icon: '❔', label: 'Помощь' },
]

export default function TabBar() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  function handleTab(path: string) {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
    navigate(path)
  }

  return (
    <nav className={s.bar}>
      {TABS.map(tab => (
        <button
          key={tab.path}
          className={`${s.item} ${pathname.startsWith(tab.path) ? s.active : ''}`}
          onClick={() => handleTab(tab.path)}
        >
          <span className={s.icon}>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}

