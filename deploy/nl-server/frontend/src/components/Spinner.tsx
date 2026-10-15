import s from './Spinner.module.css'

interface Props {
  label?: string
}

export default function Spinner({ label = 'Загружаю...' }: Props) {
  return (
    <div className={s.wrap}>
      <div className={s.ring} />
      {label}
    </div>
  )
}
