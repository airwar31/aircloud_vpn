import s from './HelpPage.module.css'

export default function HelpPage() {
  return (
    <div className={s.page}>
      <div className={s.hero}>
        <div className={s.heroTitle}>Помощь и установка</div>
        <div className={s.heroText}>
          Если подключение не работает, сначала обновите подписку и проверьте срок действия ключей.
        </div>
      </div>

      <div className="section-label">Быстрый старт</div>
      <div className={s.card}>
        <div className={s.row}>1. Скопируйте «Ссылку подписки» во вкладке «Подписка».</div>
        <div className={s.row}>2. Добавьте URL в VPN-клиент.</div>
        <div className={s.row}>3. Нажмите «Обновить» в клиенте.</div>
        <div className={s.row}>4. Выберите сервер и подключитесь.</div>
      </div>

      <div className="section-label">Клиенты</div>
      <div className={s.card}>
        <div className={s.row}>Windows: V2rayN, Clash for Windows</div>
        <div className={s.row}>Android: NekoBox, V2rayNG</div>
        <div className={s.row}>iOS/macOS: Shadowrocket/другие VLESS-клиенты</div>
      </div>

      <div className="section-label">Если не подключается</div>
      <div className={s.card}>
        <div className={s.row}>Проверьте, что дата подписки ещё не истекла.</div>
        <div className={s.row}>Переимпортируйте ссылку подписки из бота.</div>
        <div className={s.row}>Смените тип тоннеля: «Нидерланды» - «Двойной тоннель».</div>
      </div>
    </div>
  )
}

