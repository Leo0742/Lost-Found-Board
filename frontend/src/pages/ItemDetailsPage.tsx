import { useEffect, useMemo, useState } from 'react'
import { AxiosError } from 'axios'
import { Link, useParams } from 'react-router-dom'
import { claimAction, createClaim, fetchItem, fetchMatches, flagItem, getAuthMe, listClaims, shareClaimLiveLocation } from '../api/items'
import { Claim, Item, MatchResult } from '../types/item'
import { EmptyState, LoadingGrid, SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

const normalizeImageSrc = (value?: string | null) => {
  if (!value) return null
  if (value.startsWith('/media/')) return value
  if (/^https?:\/\//i.test(value)) return value
  return `/media/${value.replace(/^\/+/, '')}`
}

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
  const [isImagePreviewOpen, setIsImagePreviewOpen] = useState(false)
  const [claimFeedback, setClaimFeedback] = useState<{ tone: 'success' | 'error'; message: string } | null>(null)
  const [startClaimLoadingId, setStartClaimLoadingId] = useState<number | null>(null)
  const [claimActionLoadingId, setClaimActionLoadingId] = useState<number | null>(null)
  const [liveLocationLoadingId, setLiveLocationLoadingId] = useState<number | null>(null)

  useEffect(() => {
    if (!id) return
    void (async () => {
      const [nextItem, nextMatches] = await Promise.all([fetchItem(id), fetchMatches(id)])
      setItem(nextItem)
      setMatches(nextMatches)
      const me = await getAuthMe()
      const telegramId = me.identity?.telegram_user_id ?? null
      setOwnerId(telegramId)
      if (telegramId) setClaims(await listClaims('all') as Claim[])
    })()
  }, [id])

  const relatedClaims = useMemo(() => claims.filter((c) => c.source_item_id === item?.id || c.target_item_id === item?.id), [claims, item?.id])

  const reloadClaims = async () => {
    if (!ownerId) return
    setClaims(await listClaims('all') as Claim[])
  }

  const claimStatusLabel = (status: Claim['status']) => t(`item.claim.status.${status}`)
  const toErrorMessage = (error: unknown) => {
    const fallback = t('item.claim.startFailed')
    if (error instanceof AxiosError) {
      const detail = error.response?.data?.detail
      if (typeof detail === 'string' && detail.trim()) return detail
    }
    return fallback
  }

  const existingClaimForPair = (sourceItemId: number, targetItemId: number) => {
    return claims.find((claim) => (
      (claim.source_item_id === sourceItemId && claim.target_item_id === targetItemId)
      || (claim.source_item_id === targetItemId && claim.target_item_id === sourceItemId)
    ))
  }

  const statusFeedbackKey: Partial<Record<Claim['status'], string>> = {
    pending: 'item.claim.startState.pending',
    approved: 'item.claim.startState.approved',
    completed: 'item.claim.startState.completed',
    not_match: 'item.claim.startState.notMatch',
    rejected: 'item.claim.startState.rejected',
    cancelled: 'item.claim.startState.cancelled',
  }

  const startClaimForMatch = async (match: MatchResult) => {
    if (!item || !ownerId) return
    setClaimFeedback(null)
    const existing = existingClaimForPair(item.id, match.id)
    if (existing && statusFeedbackKey[existing.status]) {
      setClaimFeedback({ tone: 'success', message: t(statusFeedbackKey[existing.status] ?? 'item.claim.startState.pending') })
      return
    }
    setStartClaimLoadingId(match.id)
    try {
      await createClaim(item.id, match.id)
      await reloadClaims()
      setClaimFeedback({ tone: 'success', message: t('item.claim.startSuccess') })
    } catch (error) {
      setClaimFeedback({ tone: 'error', message: toErrorMessage(error) })
    } finally {
      setStartClaimLoadingId(null)
    }
  }

  const runClaimAction = async (claimId: number, action: 'approve' | 'reject' | 'complete') => {
    setClaimActionLoadingId(claimId)
    setClaimFeedback(null)
    try {
      await claimAction(claimId, action)
      await reloadClaims()
      setClaimFeedback({ tone: 'success', message: t(`item.claim.action.${action}.success`) })
    } catch (error) {
      setClaimFeedback({ tone: 'error', message: toErrorMessage(error) })
    } finally {
      setClaimActionLoadingId(null)
    }
  }

  const shareLiveLocationForClaim = async (claimId: number) => {
    if (!navigator.geolocation) {
      setClaimFeedback({ tone: 'error', message: t('item.claim.liveLocationUnsupported') })
      return
    }
    setLiveLocationLoadingId(claimId)
    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        await shareClaimLiveLocation(claimId, {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          ttl_minutes: 120,
        })
        await reloadClaims()
        setClaimFeedback({ tone: 'success', message: t('item.claim.liveLocationShared') })
      } catch (error) {
        setClaimFeedback({ tone: 'error', message: toErrorMessage(error) })
      } finally {
        setLiveLocationLoadingId(null)
      }
    }, () => {
      setLiveLocationLoadingId(null)
      setClaimFeedback({ tone: 'error', message: t('item.claim.liveLocationFailed') })
    })
  }

  if (!item) return <LoadingGrid count={2} />

  return (
    <section className="stack">
      <div className="reports-tabs item-details-tabs" role="tablist" aria-label="Item details tabs">
        <button type="button" role="tab" aria-selected={activeTab === 'overview'} className={`reports-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          {t('item.tab.overview')} <span>{item.status.toUpperCase()}</span>
        </button>
        <button type="button" role="tab" aria-selected={activeTab === 'matches'} className={`reports-tab ${activeTab === 'matches' ? 'active' : ''}`} onClick={() => setActiveTab('matches')}>
          {t('item.tab.matches')} <span>{matches.length}</span>
        </button>
        <button type="button" role="tab" aria-selected={activeTab === 'claims'} className={`reports-tab ${activeTab === 'claims' ? 'active' : ''}`} onClick={() => setActiveTab('claims')}>
          {t('item.tab.claims')} <span>{relatedClaims.length}</span>
        </button>
      </div>

      {activeTab === 'overview' ? (
        <SectionCard title={t('item.overview.title')} subtitle={t('item.overview.subtitle')}>
          {normalizeImageSrc(item.image_path) ? (
            <>
              <button type="button" className="item-detail-image-frame" onClick={() => setIsImagePreviewOpen(true)}>
                <img className="item-detail-image" src={normalizeImageSrc(item.image_path) ?? ''} alt={item.title} />
              </button>
              {isImagePreviewOpen && normalizeImageSrc(item.image_path) ? (
                <div className="item-image-lightbox" role="dialog" aria-modal="true" aria-label={t('item.image.expandedLabel')} onClick={() => setIsImagePreviewOpen(false)}>
                  <button type="button" className="item-image-lightbox-close" onClick={() => setIsImagePreviewOpen(false)}>{t('item.close')}</button>
                  <img className="item-image-lightbox-content" src={normalizeImageSrc(item.image_path) ?? ''} alt={item.title} onClick={(e) => e.stopPropagation()} />
                </div>
              ) : null}
            </>
          ) : <div className="detail-image" aria-hidden="true" />}
          <div className="status-row">
            <span className={`badge ${item.status}`}>{item.status.toUpperCase()}</span>
          </div>
          <h2>{item.title}</h2>
          <p>{item.description}</p>
          <div className="kpi-grid">
            <div className="kpi"><strong>{item.category}</strong><span className="subtle">{t('board.filter.category')}</span></div>
            <div className="kpi"><strong>{item.location}</strong><span className="subtle">{t('board.filter.location')}</span></div>
            <div className="kpi"><strong>{item.contact_name || t('item.hiddenUntilClaim')}</strong><span className="subtle">{t('item.contact')}</span></div>
            <div className="kpi"><strong>{item.telegram_username || t('item.hidden')}</strong><span className="subtle">{t('item.telegram')}</span></div>
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
          {claimFeedback ? <p className={`notice ${claimFeedback.tone === 'error' ? 'error' : 'success'}`}>{claimFeedback.message}</p> : null}
          {matches.length === 0 ? <EmptyState title={t('item.matches.emptyTitle')} subtitle={t('item.matches.emptySubtitle')} /> : (
            <div className="claim-grid item-match-grid">
              {matches.map((match) => (
                <article key={match.id} className="card stack">
                  {normalizeImageSrc(match.image_path) ? <img className="match-thumb item-match-thumb" src={normalizeImageSrc(match.image_path) ?? ''} alt={match.title} /> : null}
                  <strong>{match.title}</strong>
                  <p className="subtle">{match.category} · {match.location}</p>
                  <div className="status-row">
                    <span className="badge active">{match.relevance_score}/10</span>
                    <span className={`badge ${match.confidence === 'high' ? 'approved' : 'pending'}`}>{match.confidence}</span>
                  </div>
                  <p className="subtle">{match.reasons.join(', ')}</p>
                  {ownerId ? (
                    <button type="button" disabled={startClaimLoadingId === match.id} onClick={() => void startClaimForMatch(match)}>
                      {startClaimLoadingId === match.id ? t('item.claim.startLoading') : t('item.startClaim')}
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          )}
          <Link className="subtle" to="/">{t('item.back')}</Link>
        </SectionCard>
      ) : null}

      {activeTab === 'claims' ? (
        <SectionCard title={t('item.claims.title')} subtitle={t('item.claims.subtitle')}>
          {claimFeedback ? <p className={`notice ${claimFeedback.tone === 'error' ? 'error' : 'success'}`}>{claimFeedback.message}</p> : null}
          {relatedClaims.length === 0 ? <p className="subtle">{t('item.claims.empty')}</p> : relatedClaims.map((claim) => (
            <article key={claim.id} className="card stack">
              <div className="meta"><strong>{t('item.claim.label')}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claimStatusLabel(claim.status)}</span></div>
              <small className="subtle">{claim.source_item_title || t('item.claim.participant.source')} → {claim.target_item_title || t('item.claim.participant.target')}</small>
              {claim.status === 'pending' && claim.owner_telegram_user_id === ownerId ? (
                <div className="actions-row">
                  <button type="button" disabled={claimActionLoadingId === claim.id} onClick={() => void runClaimAction(claim.id, 'approve')}>{t('item.approve')}</button>
                  <button className="button-neutral" type="button" disabled={claimActionLoadingId === claim.id} onClick={() => void runClaimAction(claim.id, 'reject')}>{t('item.reject')}</button>
                </div>
              ) : null}
              {claim.status === 'approved' || claim.status === 'completed' ? (
                <>
                  <p className="notice">{t('item.sharedContacts')}: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p>
                  {(claim.shared_source_address || claim.shared_target_address) ? <p className="subtle">{t('item.claim.address')}: {claim.shared_source_address || '-'} / {claim.shared_target_address || '-'}</p> : null}
                  <div className="actions-row">
                    {claim.shared_source_route_url ? <a href={claim.shared_source_route_url} target="_blank" rel="noreferrer"><button type="button" className="button-neutral">{t('item.claim.buildRouteSource')}</button></a> : null}
                    {claim.shared_target_route_url ? <a href={claim.shared_target_route_url} target="_blank" rel="noreferrer"><button type="button" className="button-neutral">{t('item.claim.buildRouteTarget')}</button></a> : null}
                    <button type="button" className="button-neutral" disabled={liveLocationLoadingId === claim.id} onClick={() => void shareLiveLocationForClaim(claim.id)}>{liveLocationLoadingId === claim.id ? t('item.claim.liveLocationLoading') : t('item.claim.shareLocation')}</button>
                    {claim.shared_live_location?.route_url ? <a href={claim.shared_live_location.route_url} target="_blank" rel="noreferrer"><button type="button">{t('item.claim.openLiveMeetup')}</button></a> : null}
                    {claim.status === 'approved' ? <button type="button" className="button-neutral" disabled={claimActionLoadingId === claim.id} onClick={() => void runClaimAction(claim.id, 'complete')}>{t('item.claim.returned')}</button> : null}
                  </div>
                  {claim.shared_live_location ? <p className="subtle">{t('item.claim.liveLocationUntil', { until: new Date(claim.shared_live_location.expires_at).toLocaleString() })}</p> : null}
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
