import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { claimAction, createClaim, fetchItem, fetchMatches, flagItem, getAuthMe, listClaims } from '../api/items'
import { Claim, Item, MatchResult } from '../types/item'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'

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
      if (telegramId) setClaims(await listClaims(undefined, 'all') as Claim[])
    })
  }, [id])

  const relatedClaims = useMemo(() => claims.filter((c) => c.source_item_id === item?.id || c.target_item_id === item?.id), [claims, item?.id])

  if (!item) return <LoadingGrid count={2} />

  return (
    <section className="stack">
      <PageHero
        title={`${item.title} · report workspace`}
        subtitle="Review status, evaluate smart matches, and manage claim handoff from one structured workspace."
        stats={[
          { label: 'Lifecycle', value: item.lifecycle },
          { label: 'Moderation', value: item.moderation_status },
          { label: 'Verified', value: item.is_verified ? 'Yes' : 'No' },
          { label: 'Claims', value: relatedClaims.length },
        ]}
      />

      <div className="layout-three">
        <SectionCard title="Report overview" subtitle="Core details and trust signals.">
          {item.image_path ? <img className="detail-image" src={`/media/${item.image_path}`} alt={item.title} /> : <div className="detail-image" aria-hidden="true" />}
          <div className="status-row">
            <span className={`badge ${item.status}`}>{item.status}</span>
            <span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span>
            <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
            <span className="badge approved">{item.is_verified ? 'verified' : 'unverified'}</span>
          </div>
          <p>{item.description}</p>
          <div className="kpi-grid">
            <div className="kpi"><strong>{item.category}</strong><span className="subtle">Category</span></div>
            <div className="kpi"><strong>{item.location}</strong><span className="subtle">Location</span></div>
            <div className="kpi"><strong>{item.contact_name}</strong><span className="subtle">Contact</span></div>
            <div className="kpi"><strong>{item.telegram_username || 'N/A'}</strong><span className="subtle">Telegram</span></div>
          </div>
        </SectionCard>

        <SectionCard title="Smart matches" subtitle="Visual candidate board with immediate claim actions.">
          {matches.length === 0 ? <EmptyState title="No likely matches yet" subtitle="New opposite-status reports will appear automatically." /> : (
            <div className="claim-grid">
              {matches.map((match) => (
                <article key={match.id} className="card stack">
                  {match.image_path ? <img className="match-thumb" src={`/media/${match.image_path}`} alt={match.title} /> : null}
                  <strong>{match.title}</strong>
                  <p className="subtle">{match.category} · {match.location}</p>
                  <div className="status-row">
                    <span className="badge active">{match.relevance_score}/10</span>
                    <span className={`badge ${match.confidence === 'high' ? 'approved' : 'pending'}`}>{match.confidence}</span>
                  </div>
                  <p className="subtle">{match.reasons.join(', ')}</p>
                  {ownerId ? <button type="button" onClick={async () => { await createClaim(item.id, match.id); setClaims(await listClaims(undefined, 'all') as Claim[]) }}>Start claim handoff</button> : null}
                </article>
              ))}
            </div>
          )}
        </SectionCard>

        <div className="stack sticky-side">
          <SectionCard title="Claims & handoff" subtitle="Action queue for this report only.">
            {relatedClaims.length === 0 ? <p className="subtle">No claim requests yet.</p> : relatedClaims.map((claim) => (
              <article key={claim.id} className="card stack">
                <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
                <small className="subtle">#{claim.source_item_id} → #{claim.target_item_id}</small>
                {claim.status === 'pending' && claim.owner_telegram_user_id === ownerId ? (
                  <div className="actions-row">
                    <button type="button" onClick={async () => { await claimAction(claim.id, 'approve'); setClaims(await listClaims(undefined, 'all') as Claim[]) }}>Approve</button>
                    <button className="button-neutral" type="button" onClick={async () => { await claimAction(claim.id, 'reject'); setClaims(await listClaims(undefined, 'all') as Claim[]) }}>Reject</button>
                  </div>
                ) : null}
                {claim.status === 'approved' ? <p className="notice">Shared contacts: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p> : null}
              </article>
            ))}
          </SectionCard>

          <SectionCard title="Safety" subtitle="Flag suspicious records for moderation.">
            <select value={flagReason} onChange={(e) => setFlagReason(e.target.value)}>
              <option value="spam">spam</option><option value="fake item">fake item</option><option value="abusive content">abusive content</option><option value="duplicate">duplicate</option><option value="other">other</option>
            </select>
            <button type="button" onClick={async () => { await flagItem(item.id, flagReason); setFlagMessage('Report flagged for admin review.'); setItem(await fetchItem(String(item.id))) }}>Flag report</button>
            {flagMessage ? <p className="notice">{flagMessage}</p> : null}
          </SectionCard>
          <Link className="subtle" to="/">← Back to list</Link>
        </div>
      </div>
    </section>
  )
}
