import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchItem, fetchMatches } from '../api/items'
import { Item, MatchResult } from '../types/item'

export const ItemDetailsPage = () => {
  const { id } = useParams<{ id: string }>()
  const [item, setItem] = useState<Item | null>(null)
  const [matches, setMatches] = useState<MatchResult[]>([])

  useEffect(() => {
    if (!id) return
    fetchItem(id).then(setItem)
    fetchMatches(id).then(setMatches)
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
      <p>
        Lifecycle: <strong>{item.lifecycle}</strong>
      </p>
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

      <section className="matches-block">
        <h2>Smart Matches</h2>
        {matches.length === 0 ? (
          <p className="subtle">No likely opposite-status matches yet.</p>
        ) : (
          <ul className="matches-list">
            {matches.map((match) => (
              <li key={match.id}>
                <strong>{match.title}</strong> — {match.category}, {match.location}
                <div>
                  Score: {match.relevance_score} / 10 · Confidence: {match.confidence}
                </div>
                <small>Why: {match.reasons.join(', ')}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
      <Link to="/">Back to list</Link>
    </article>
  )
}
