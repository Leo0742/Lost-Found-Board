import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchItem } from '../api/items'
import { Item } from '../types/item'

export const ItemDetailsPage = () => {
  const { id } = useParams<{ id: string }>()
  const [item, setItem] = useState<Item | null>(null)

  useEffect(() => {
    if (!id) return
    fetchItem(id).then(setItem)
  }, [id])

  if (!item) {
    return <p>Loading item...</p>
  }

  return (
    <article className="details">
      <div className="card-head">
        <h1>{item.title}</h1>
        <span className={`badge ${item.status}`}>{item.status}</span>
      </div>
      <p>{item.description}</p>
      <ul>
        <li>
          <strong>Category:</strong> {item.category}
        </li>
        <li>
          <strong>Location:</strong> {item.location}
        </li>
        <li>
          <strong>Contact:</strong> {item.contact_name}
        </li>
        <li>
          <strong>Telegram:</strong> {item.telegram_username || 'Not provided'}
        </li>
      </ul>
      <Link to="/">Back to list</Link>
    </article>
  )
}
