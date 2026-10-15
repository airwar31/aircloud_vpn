import { useState, useEffect, useCallback } from 'react'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import type { SubscriptionData } from './types'
import { getUserSubscription } from './api'
import { AppContext } from './context'
import Spinner from './components/Spinner'
import TabBar from './components/TabBar'
import SubscriptionPage from './pages/SubscriptionPage'
import BuyPage from './pages/BuyPage/BuyPage'
import HelpPage from './pages/HelpPage'
import './global.css'

export default function App() {
  const tg = window.Telegram?.WebApp
  const userId = tg?.initDataUnsafe?.user?.id ?? null

  const [loading, setLoading] = useState(true)
  const [subData, setSubData] = useState<SubscriptionData | null>(null)
  const [authError, setAuthError] = useState(false)

  const refreshSub = useCallback(async () => {
    if (!userId) return
    try {
      const data = await getUserSubscription(userId)
      setSubData(data)
    } catch {
      // keep previous data on refresh error
    }
  }, [userId])

  useEffect(() => {
    tg?.expand()
    tg?.ready()

    if (!userId) {
      setAuthError(true)
      setLoading(false)
      return
    }

    getUserSubscription(userId)
      .then(data => setSubData(data))
      .catch(() => {
        // fallback to empty state
        setSubData({ keys: [], subscription_url: null })
      })
      .finally(() => setLoading(false))
  }, [userId])

  if (loading) {
    return (
      <div style={{ padding: '0 16px' }}>
        <Header userId={userId} />
        <Spinner label="Загружаем данные…" />
      </div>
    )
  }

  if (authError) {
    return (
      <div
        style={{
          padding: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100svh',
        }}
      >
        <div
          style={{
            background: 'var(--card)',
            borderRadius: 16,
            border: '1px solid var(--border)',
            padding: '40px 24px',
            textAlign: 'center',
            maxWidth: 320,
          }}
        >
          <div style={{ fontSize: 28, marginBottom: 12, fontWeight: 800 }}>🔒</div>
          <p style={{ color: 'var(--sub)', fontSize: 14, lineHeight: 1.6 }}>
            Откройте Mini App через Telegram-бота,
            <br />
            чтобы загрузить ваши подписки.
          </p>
        </div>
      </div>
    )
  }

  return (
    <AppContext.Provider value={{ userId, subData, refreshSub }}>
      <MemoryRouter initialEntries={['/subscription']}>
        <Header userId={userId} />
        <Routes>
          <Route path="/subscription" element={<SubscriptionPage data={subData} />} />
          <Route path="/buy/*" element={<BuyPage />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="*" element={<Navigate to="/subscription" replace />} />
        </Routes>
        <TabBar />
      </MemoryRouter>
    </AppContext.Provider>
  )
}

function Header(_props: { userId: number | null }) {
  const tg = window.Telegram?.WebApp
  const user = tg?.initDataUnsafe?.user
  const greeting = user?.first_name ? `Привет, ${user.first_name}!` : 'Управление подпиской'

  return (
    <div style={{ textAlign: 'center', padding: '18px 16px 14px' }}>
      <div style={{ fontSize: 24, marginBottom: 3, fontWeight: 800 }}>☁️</div>
      <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: '0.2px' }}>AirCloud VPN</div>
      <div style={{ color: 'var(--sub)', fontSize: 12, marginTop: 2 }}>{greeting}</div>
    </div>
  )
}

