import type { SubscriptionData, CreatePaymentBody, PaymentResult } from './types'

function getTelegramHeaders(): Record<string, string> {
  const tg = window.Telegram?.WebApp
  if (!tg?.initData) return {}
  return { 'X-Telegram-Init-Data': tg.initData }
}

export async function getUserSubscription(userId: number): Promise<SubscriptionData> {
  const resp = await fetch(`/api/user/${userId}/subscription`, {
    headers: getTelegramHeaders(),
  })
  if (!resp.ok) throw new Error(`API error ${resp.status}`)
  return resp.json()
}

export async function createPayment(body: CreatePaymentBody): Promise<PaymentResult> {
  const resp = await fetch('/api/create-payment', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getTelegramHeaders(),
    },
    body: JSON.stringify(body),
  })
  if (!resp.ok) throw new Error(`API error ${resp.status}`)
  return resp.json()
}
