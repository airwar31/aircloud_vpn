import { createContext, useContext } from 'react'
import type { SubscriptionData } from './types'

export interface AppContextValue {
  userId: number | null
  subData: SubscriptionData | null
  refreshSub: () => Promise<void>
}

export const AppContext = createContext<AppContextValue>({
  userId: null,
  subData: null,
  refreshSub: async () => {},
})

export const useApp = () => useContext(AppContext)
