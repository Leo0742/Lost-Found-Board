import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { claimAction, createClaim, fetchItem, fetchMatches, flagItem, getAuthMe, listClaims } from '../api/items'
import { Claim, Item, MatchResult } from '../types/item'

export const ItemDetailsPage = () => {
  const { id } = useParams<{ id: string }>()
  const [item, setItem] = useState<Item | null>(null)
  const [matches, setMatches] = useState<MatchResult[]>([])
  const [flagReason, setFlagReason] = useState('spam')
  const [flagMessage, setFlagMessage] = useState<string | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [ownerId, setOwnerId] = useState<number | null>(null)

  useEffect(() => {
    if (!id) return
    fetchItem(id).then(setItem)
    fetchMatches(id).then(setMatches)
    getAuthMe().then(async (me) => {
      const telegramId = me.identity?.telegram_user_id ?? null
      setOwnerId(telegramId)
      if (telegramId) {
        const data = await listClaims(undefined, 'all')
        setClaims(data as Claim[])
      }
    })
  }, [id])

  if (!item) return <p>Loading item...</p>

  return (
    <article className="details">
      {item.image_path ? <img className="detail-image" src={`/media/${item.image_path}`} alt={item.title} /> : null}
      <div className="card-head">
        <h1>{item.title}</h1>
        <span className={`badge ${item.status}`}>{item.status}</span>
      </div>
      <p>Lifecycle: <strong>{item.lifecycle}</strong></p>
      <p>Moderation: <strong>{item.moderation_status}</strong> {item.is_verified ? '✅ Verified report' : 'Unverified'}</p>
      <p>{item.description}</p>
      <ul>
        <li><strong>Category:</strong> {item.category}</li>
        <li><strong>Location:</strong> {item.location}</li>
        <li><strong>Contact:</strong> {item.contact_name}</li>
        <li><strong>Telegram:</strong> {item.telegram_username || 'Not provided'}</li>
      </ul>

      <section className="matches-block">
        <h2>Smart Matches</h2>
        {matches.length === 0 ? <p className="subtle">No likely opposite-status matches yet.</p> : (
          <ul className="matches-list">
            {matches.map((match) => (
              <li key={match.id}>
                {match.image_path ? <img className="match-thumb" src={`/media/${match.image_path}`} alt={match.title} /> : null}
                <strong>{match.title}</strong> — {match.category}, {match.location}
                <div>Score: {match.relevance_score} / 10 · Confidence: {match.confidence}</div>
                <small>Why: {match.reasons.join(', ')}</small>
                {ownerId && (
                  <button type="button" onClick={async () => {
                    await createClaim(item.id, match.id)
                    const updated = await listClaims(undefined, 'all')
                    setClaims(updated as Claim[])
                  }}>Claim this match</button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {ownerId ? (
        <section className="matches-block">
          <h3>Claims related to this report</h3>
          {claims.filter((claim) => claim.source_item_id === item.id || claim.target_item_id === item.id).map((claim) => (
            <div key={claim.id} className="card">
              <strong>Claim #{claim.id}</strong> — {claim.status}
              <div>From #{claim.source_item_id} to #{claim.target_item_id}</div>
              {claim.status === 'pending' && claim.owner_telegram_user_id === ownerId ? (
                <div className="actions-row">
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'approve'); setClaims(await listClaims(undefined, 'all') as Claim[]) }}>Approve</button>
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'reject'); setClaims(await listClaims(undefined, 'all') as Claim[]) }}>Reject</button>
                </div>
              ) : null}
              {claim.status === 'approved' ? <p className="subtle">Contacts: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p> : null}
            </div>
          ))}
        </section>
      ) : null}

      <section className="form">
        <h3>Report issue</h3>
        <select value={flagReason} onChange={(e) => setFlagReason(e.target.value)}>
          <option value="spam">spam</option>
          <option value="fake item">fake item</option>
          <option value="abusive content">abusive content</option>
          <option value="duplicate">duplicate</option>
          <option value="other">other</option>
        </select>
        <button type="button" onClick={async () => { await flagItem(item.id, flagReason); setFlagMessage('Report flagged for admin review.'); setItem(await fetchItem(String(item.id))) }}>
          Flag report
        </button>
        {flagMessage ? <p className="subtle">{flagMessage}</p> : null}
      </section>
      <Link to="/">Back to list</Link>
    </article>
  )
}
