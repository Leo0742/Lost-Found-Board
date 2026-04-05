import { Link } from 'react-router-dom'
import { Item } from '../types/item'
import { useSettings } from '../context/SettingsContext'

const formatRelativeTime = (value: string, t: (key: string, params?: Record<string, string | number>) => string, language: 'en' | 'ru') => {
  const timestamp = new Date(value).getTime()
  const diffHours = Math.round((Date.now() - timestamp) / (1000 * 60 * 60))

  if (diffHours < 1) return t('board.justNow')
  if (diffHours < 24) return t('board.hoursAgo', { count: diffHours })
  const diffDays = Math.round(diffHours / 24)
  if (diffDays < 7) return t('board.daysAgo', { count: diffDays })

  return new Date(value).toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US')
}

export const ItemCard = ({ item }: { item: Item }) => {
  const imageUrl = item.image_path ? `/media/${item.image_path}` : null
  const { t, language } = useSettings()

  return (
    <article className="board-card stack">
      {imageUrl ? <img className="thumb" src={imageUrl} alt={item.title} loading="lazy" /> : <div className="thumb thumb-placeholder" aria-hidden="true">{t('board.noPhoto')}</div>}
      <div className="card-head">
        <div className="stack" style={{ gap: '.4rem' }}>
          <div className="status-row">
            <span className={`badge ${item.status}`}>{item.status}</span>
            {item.is_verified ? <span className="badge approved">{t('status.verified')}</span> : null}
            <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
          </div>
          <h3>
            <Link to={`/items/${item.id}`}>{item.title}</Link>
          </h3>
        </div>
      </div>
      <p className="subtle clamp-2">{item.description.slice(0, 160)}{item.description.length > 160 ? '…' : ''}</p>
      <div className="meta">
        <span>{item.category}</span>
        <span>{item.location}</span>
      </div>
      <div className="meta">
        <span>#{item.id}</span>
        <span>{formatRelativeTime(item.created_at, t, language)}</span>
      </div>
      <Link to={`/items/${item.id}`}><button type="button" className="button-neutral card-cta">{t('board.openDetails')}</button></Link>
    </article>
  )
}
