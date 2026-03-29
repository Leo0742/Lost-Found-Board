import { Link } from 'react-router-dom'
import { Item } from '../types/item'

export const ItemCard = ({ item }: { item: Item }) => {
  return (
    <article className="card">
      <div className="card-head">
        <h3>
          <Link to={`/items/${item.id}`}>{item.title}</Link>
        </h3>
        <span className={`badge ${item.status}`}>{item.status}</span>
      </div>
      <p>
        Lifecycle: <strong>{item.lifecycle}</strong>
      </p>
      <p>{item.description}</p>
      <div className="meta">
        <span>{item.category}</span>
        <span>{item.location}</span>
      </div>
    </article>
  )
}
