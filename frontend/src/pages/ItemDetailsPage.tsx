import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { claimAction, createClaim, fetchItem, fetchMatches, flagItem, getAuthMe, listClaims, shareClaimLiveLocation } from '../api/items'
import { Claim, Item, MatchResult } from '../types/item'
import { EmptyState, LoadingGrid, SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

export const ItemDetailsPage = () => {
  const { t } = useSettings()
  const { id } = useParams<{ id: string }>()
  const [item, setItem] = useState<Item | null>(null)
  const [matches, setMatches] = useState<MatchResult[]>([])
  const [flagReason, setFlagReason] = useState('spam')
  const [flagMessage, setFlagMessage] = useState<string | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [ownerId, setOwnerId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'matches' | 'claims'>('overview')

  useEffect(() => {
    if (!id) return
    fetchItem(id).then(setItem)
    fetchMatches(id).then(setMatches)
    getAuthMe().then(async (me) => {
      const telegramId = me.identity?.telegram_user_id ?? null
      setOwnerId(telegramId)
      if (telegramId) setClaims(await listClaims('all') as Claim[])
    })
  }, [id])

  const relatedClaims = useMemo(() => claims.filter((c) => c.source_item_id === item?.id || c.target_item_id === item?.id), [claims, item?.id])

  const shareLiveLocationForClaim = async (claimId: number) => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(async (position) => {
      await shareClaimLiveLocation(claimId, {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        ttl_minutes: 120,
      })
      if (ownerId) setClaims(await listClaims('all') as Claim[])
    })
  }

  if (!item) return <LoadingGrid count={2} />

  return (
    <section className="stack">
      <div className="reports-tabs item-details-tabs" role="tablist" aria-label="Item details tabs">
        <button type="button" role="tab" aria-selected={activeTab === 'overview'} className={`reports-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          Overview <span>{item.lifecycle}</span>
        </button>
        <button type="button" role="tab" aria-selected={activeTab === 'matches'} className={`reports-tab ${activeTab === 'matches' ? 'active' : ''}`} onClick={() => setActiveTab('matches')}>
          Matches <span>{matches.length}</span>
        </button>
        <button type="button" role="tab" aria-selected={activeTab === 'claims'} className={`reports-tab ${activeTab === 'claims' ? 'active' : ''}`} onClick={() => setActiveTab('claims')}>
          Claims & handoff <span>{relatedClaims.length}</span>
        </button>
      </div>

      {activeTab === 'overview' ? (
        <SectionCard title={t('item.overview.title')} subtitle={t('item.overview.subtitle')}>
          {item.image_path ? <img className="detail-image" src={`/media/${item.image_path}`} alt={item.title} /> : <div className="detail-image" aria-hidden="true" />}
          <div className="status-row">
            <span className={`badge ${item.status}`}>{item.status}</span>
            <span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span>
            <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
            <span className="badge approved">{item.is_verified ? t('status.verified') : t('status.unverified')}</span>
          </div>
          <h2>{item.title}</h2>
          <p>{item.description}</p>
          <div className="kpi-grid">
            <div className="kpi"><strong>{item.category}</strong><span className="subtle">{t('board.filter.category')}</span></div>
            <div className="kpi"><strong>{item.location}</strong><span className="subtle">{t('board.filter.location')}</span></div>
            <div className="kpi"><strong>{item.contact_name || t('item.hiddenUntilClaim')}</strong><span className="subtle">{t('item.contact')}</span></div>
            <div className="kpi"><strong>{item.telegram_username || t('item.hidden')}</strong><span className="subtle">Telegram</span></div>
          </div>
          <details className="item-problem-report">
            <summary>{t('item.safety.title')}</summary>
            <p className="subtle">{t('item.safety.subtitle')}</p>
            <div className="item-problem-controls">
              <select value={flagReason} onChange={(e) => setFlagReason(e.target.value)}>
                <option value="spam">spam</option><option value="fake item">fake item</option><option value="abusive content">abusive content</option><option value="duplicate">duplicate</option><option value="other">other</option>
              </select>
              <button type="button" onClick={async () => { await flagItem(item.id, flagReason); setFlagMessage(t('item.flagged')); setItem(await fetchItem(String(item.id))) }}>{t('item.flagReport')}</button>
            </div>
            {flagMessage ? <p className="notice">{flagMessage}</p> : null}
          </details>
          <Link className="subtle" to="/">{t('item.back')}</Link>
        </SectionCard>
      ) : null}

      {activeTab === 'matches' ? (
        <SectionCard title={t('item.matches.title')} subtitle={t('item.matches.subtitle')}>
          {matches.length === 0 ? <EmptyState title={t('item.matches.emptyTitle')} subtitle={t('item.matches.emptySubtitle')} /> : (
            <div className="claim-grid item-match-grid">
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
                  {ownerId ? <button type="button" onClick={async () => { await createClaim(item.id, match.id); setClaims(await listClaims('all') as Claim[]) }}>{t('item.startClaim')}</button> : null}
                </article>
              ))}
            </div>
          )}
          <Link className="subtle" to="/">{t('item.back')}</Link>
        </SectionCard>
      ) : null}

      {activeTab === 'claims' ? (
        <SectionCard title={t('item.claims.title')} subtitle={t('item.claims.subtitle')}>
          {relatedClaims.length === 0 ? <p className="subtle">{t('item.claims.empty')}</p> : relatedClaims.map((claim) => (
            <article key={claim.id} className="card stack">
              <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
              <small className="subtle">#{claim.source_item_id} → #{claim.target_item_id}</small>
              {claim.status === 'pending' && claim.owner_telegram_user_id === ownerId ? (
                <div className="actions-row">
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'approve'); setClaims(await listClaims('all') as Claim[]) }}>{t('item.approve')}</button>
                  <button className="button-neutral" type="button" onClick={async () => { await claimAction(claim.id, 'reject'); setClaims(await listClaims('all') as Claim[]) }}>{t('item.reject')}</button>
                </div>
              ) : null}
              {claim.status === 'approved' ? (
                <>
                  <p className="notice">{t('item.sharedContacts')}: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p>
                  {(claim.shared_source_address || claim.shared_target_address) ? <p className="subtle">Address: {claim.shared_source_address || '-'} / {claim.shared_target_address || '-'}</p> : null}
                  <div className="actions-row">
                    {claim.shared_source_route_url ? <a href={claim.shared_source_route_url} target="_blank" rel="noreferrer"><button type="button" className="button-neutral">Build route (source)</button></a> : null}
                    {claim.shared_target_route_url ? <a href={claim.shared_target_route_url} target="_blank" rel="noreferrer"><button type="button" className="button-neutral">Build route (target)</button></a> : null}
                    <button type="button" className="button-neutral" onClick={() => shareLiveLocationForClaim(claim.id)}>Share current location</button>
                    {claim.shared_live_location?.route_url ? <a href={claim.shared_live_location.route_url} target="_blank" rel="noreferrer"><button type="button">Open live meetup</button></a> : null}
                  </div>
                  {claim.shared_live_location ? <p className="subtle">Live location shared until {new Date(claim.shared_live_location.expires_at).toLocaleString()}</p> : null}
                </>
              ) : null}
            </article>
          ))}
          <Link className="subtle" to="/">{t('item.back')}</Link>
        </SectionCard>
      ) : null}
    </section>
  )
}
