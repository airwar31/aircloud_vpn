export type TunnelType = 'single' | 'double'
export type Duration = '1_month' | '3_months' | '12_months'
export type PaymentMethod = 'stars' | 'yookassa'

export interface VpnKey {
  tunnel_type: TunnelType
  expires_at: number | string
  email: string
  vless_link: string
}

export interface SubscriptionData {
  keys: VpnKey[]
  subscription_url: string | null
}

export interface CreatePaymentBody {
  user_id: number
  tunnel_type: TunnelType
  duration: Duration
  method: PaymentMethod
}

export interface PaymentResult {
  type: 'invoice' | 'url'
  invoice_link?: string
  url?: string
  payment_id?: string
}

export type BuyStep = 'plan' | 'dur' | 'pay' | 'result'

export interface BuyState {
  plan: TunnelType | null
  duration: Duration | null
  method: PaymentMethod | null
}
