interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
}

interface HapticFeedback {
  impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
  notificationOccurred(type: 'error' | 'success' | 'warning'): void
  selectionChanged(): void
}

interface WebApp {
  initData: string
  initDataUnsafe: {
    user?: TelegramUser
    [key: string]: unknown
  }
  expand(): void
  ready(): void
  close(): void
  openLink(url: string, options?: { try_instant_view?: boolean }): void
  openInvoice(url: string, callback?: (status: string) => void): void
  HapticFeedback?: HapticFeedback
  themeParams: {
    bg_color?: string
    text_color?: string
    [key: string]: string | undefined
  }
}

interface Window {
  Telegram: {
    WebApp: WebApp
  }
}
