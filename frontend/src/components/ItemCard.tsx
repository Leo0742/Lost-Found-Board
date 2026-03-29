import { Link } from 'react-router-dom'
import { Item } from '../types/item'

const formatDate = (value: string) => new Date(value).toLocaleDateString()

export const ItemCard = ({ item }: { item: Item }) => {
  const imageUrl = item.image_path ? `/media/${item.image_path}` : null

  return (
    <article className="card stack">
      {imageUrl ? <img className="thumb" src={imageUrl} alt={item.title} /> : <div className="thumb" aria-hidden="true" />}
      <div className="card-head">
        <h3>
          <Link to={`/items/${item.id}`}>{item.title}</Link>
        </h3>
        <span className={`badge ${item.status}`}>{item.status}</span>
      </div>
      <div className="meta">
        <span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span>
        <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
      </div>
      <p className="subtle">{item.description.slice(0, 130)}{item.description.length > 130 ? '…' : ''}</p>
      <div className="meta">
        <span>{item.category}</span>
        <span>{item.location}</span>
      </div>
      <div className="meta">
        <span>#{item.id}</span>
        <span>{formatDate(item.created_at)}</span>
      </div>
      <Link to={`/items/${item.id}`}><button type="button" className="button-neutral">Open workspace</button></Link>
    </article>
  )
}
