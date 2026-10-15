import { Routes, Route, Navigate } from 'react-router-dom'
import PlanStep from './PlanStep'
import DurationStep from './DurationStep'
import PaymentStep from './PaymentStep'
import ResultStep from './ResultStep'
import s from './BuyPage.module.css'

export default function BuyPage() {
  return (
    <div className={s.page}>
      <Routes>
        <Route index element={<PlanStep />} />
        <Route path="dur"    element={<DurationStep />} />
        <Route path="pay"    element={<PaymentStep />} />
        <Route path="result" element={<ResultStep />} />
        <Route path="*"      element={<Navigate to="/buy" replace />} />
      </Routes>
    </div>
  )
}
