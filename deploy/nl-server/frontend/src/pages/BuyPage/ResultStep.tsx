import { useNavigate, useLocation } from 'react-router-dom'
import s from './BuyPage.module.css'

type ResultType = 'success_stars' | 'yookassa_pending' | 'cancelled' | 'failed' | 'error'

interface ResultMeta {
  icon: string
  title: string
  desc: string
  primaryLabel: string
  primaryPath: string
  secondaryLabel?: string
  secondaryPath?: string
}

const RESULTS: Record<ResultType, ResultMeta> = {
  success_stars: {
    icon: '✅',
    title: 'Оплата прошла',
    desc: 'Подписка активируется автоматически.\nОткройте вкладку «Подписка» и нажмите «Обновить».',
    primaryLabel: 'К подписке',
    primaryPath: '/subscription',
  },
  yookassa_pending: {
    icon: '⏳',
    title: 'Ожидаем оплату',
    desc: 'Завершите оплату в открытом окне YooKassa.\nПосле оплаты вернитесь и обновите подписки.',
    primaryLabel: 'К подписке',
    primaryPath: '/subscription',
    secondaryLabel: 'Выбрать другой тариф',
    secondaryPath: '/buy',
  },
  cancelled: {
    icon: '⛔',
    title: 'Оплата отменена',
    desc: 'Платёж не завершён. Можно попробовать ещё раз.',
    primaryLabel: 'Попробовать снова',
    primaryPath: '/buy',
  },
  failed: {
    icon: '⚠️',
    title: 'Не удалось обработать оплату',
    desc: 'Попробуйте ещё раз или выберите другой способ оплаты.',
    primaryLabel: 'Попробовать снова',
    primaryPath: '/buy',
  },
  error: {
    icon: '📡',
    title: 'Ошибка сети',
    desc: 'Не удалось создать платёж. Проверьте интернет и повторите.',
    primaryLabel: 'Попробовать снова',
    primaryPath: '/buy',
  },
}

export default function ResultStep() {
  const navigate = useNavigate()
  const { state } = useLocation() as { state: { resultType?: ResultType } }
  const resultType: ResultType = state?.resultType ?? 'error'
  const meta = RESULTS[resultType]

  function go(path: string) {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
    navigate(path)
  }

  return (
    <div className={s.resultCard}>
      <div className={s.resultIcon}>{meta.icon}</div>
      <div className={s.resultTitle}>{meta.title}</div>
      <div className={s.resultDesc}>
        {meta.desc.split('\n').map((line, i) => (
          <span key={i}>
            {line}
            {i < meta.desc.split('\n').length - 1 && <br />}
          </span>
        ))}
      </div>

      <button className={`${s.actionBtn} ${s.green}`} onClick={() => go(meta.primaryPath)}>
        {meta.primaryLabel}
      </button>

      {meta.secondaryLabel && meta.secondaryPath && (
        <button
          className={`${s.actionBtn} ${s.blue}`}
          style={{ marginTop: 8 }}
          onClick={() => {
            if (meta.secondaryPath) go(meta.secondaryPath)
          }}
        >
          {meta.secondaryLabel}
        </button>
      )}
    </div>
  )
}

