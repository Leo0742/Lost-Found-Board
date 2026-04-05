import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { claimAction, createClaim, fetchItem, fetchMatches, flagItem, getAuthMe, listClaims } from '../api/items'
import { Claim, Item, MatchResult } from '../types/item'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'
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

  if (!item) return <LoadingGrid count={2} />

  return (
    <section className="stack">
      <PageHero
        title={`${item.title} · ${t('item.workspace')}`}
        subtitle={t('item.heroSubtitle')}
        stats={[
          { label: t('item.stats.lifecycle'), value: item.lifecycle },
          { label: t('item.stats.moderation'), value: item.moderation_status },
          { label: t('item.stats.verified'), value: item.is_verified ? t('item.yes') : t('item.no') },
          { label: t('item.stats.claims'), value: relatedClaims.length },
        ]}
      />

      <div className="layout-three">
        <SectionCard title={t('item.overview.title')} subtitle={t('item.overview.subtitle')}>
          {item.image_path ? <img className="detail-image" src={`/media/${item.image_path}`} alt={item.title} /> : <div className="detail-image" aria-hidden="true" />}
          <div className="status-row">
            <span className={`badge ${item.status}`}>{item.status}</span>
            <span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span>
            <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
            <span className="badge approved">{item.is_verified ? t('status.verified') : t('status.unverified')}</span>
          </div>
          <p>{item.description}</p>
          <div className="kpi-grid">
            <div className="kpi"><strong>{item.category}</strong><span className="subtle">{t('board.filter.category')}</span></div>
            <div className="kpi"><strong>{item.location}</strong><span className="subtle">{t('board.filter.location')}</span></div>
            <div className="kpi"><strong>{item.contact_name || t('item.hiddenUntilClaim')}</strong><span className="subtle">{t('item.contact')}</span></div>
            <div className="kpi"><strong>{item.telegram_username || t('item.hidden')}</strong><span className="subtle">Telegram</span></div>
          </div>
        </SectionCard>

        <SectionCard title={t('item.matches.title')} subtitle={t('item.matches.subtitle')}>
          {matches.length === 0 ? <EmptyState title={t('item.matches.emptyTitle')} subtitle={t('item.matches.emptySubtitle')} /> : (
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
                  {ownerId ? <button type="button" onClick={async () => { await createClaim(item.id, match.id); setClaims(await listClaims('all') as Claim[]) }}>{t('item.startClaim')}</button> : null}
                </article>
              ))}
            </div>
          )}
        </SectionCard>

        <div className="stack sticky-side">
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
                {claim.status === 'approved' ? <p className="notice">{t('item.sharedContacts')}: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p> : null}
              </article>
            ))}
          </SectionCard>

          <SectionCard title={t('item.safety.title')} subtitle={t('item.safety.subtitle')}>
            <select value={flagReason} onChange={(e) => setFlagReason(e.target.value)}>
              <option value="spam">spam</option><option value="fake item">fake item</option><option value="abusive content">abusive content</option><option value="duplicate">duplicate</option><option value="other">other</option>
            </select>
            <button type="button" onClick={async () => { await flagItem(item.id, flagReason); setFlagMessage(t('item.flagged')); setItem(await fetchItem(String(item.id))) }}>{t('item.flagReport')}</button>
            {flagMessage ? <p className="notice">{flagMessage}</p> : null}
          </SectionCard>
          <Link className="subtle" to="/">{t('item.back')}</Link>
        </div>
      </div>
    </section>
  )
}
