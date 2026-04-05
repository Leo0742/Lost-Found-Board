import { useEffect, useMemo, useState } from 'react'
import { AxiosError } from 'axios'
import { claimAction, fetchMyItems, getAuthMe, listClaims, resolveItem, reopenItem, shareClaimLiveLocation, softDeleteItem } from '../api/items'
import { Claim, Item } from '../types/item'
import { Link } from 'react-router-dom'
import { EmptyState, LoadingGrid, SectionCard } from '../components/ui'
import { useSettings } from '../context/SettingsContext'

export const MyReportsPage = () => {
  const { t } = useSettings()
  const [items, setItems] = useState<Item[]>([])
  const [incomingClaims, setIncomingClaims] = useState<Claim[]>([])
  const [outgoingClaims, setOutgoingClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [incomingError, setIncomingError] = useState<string | null>(null)
  const [outgoingError, setOutgoingError] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'my' | 'incoming' | 'outgoing'>('my')

  const load = async () => {
    setLoading(true); setError(null); setIncomingError(null); setOutgoingError(null)
    try {
      const me = await getAuthMe()
      if (!me.linked || !me.identity?.telegram_user_id) {
        setLinkedUserId(null); setItems([]); setIncomingClaims([]); setOutgoingClaims([])
        return
      }
      setLinkedUserId(me.identity.telegram_user_id)
      setItems((await fetchMyItems()).sort((a, b) => b.id - a.id))
      try { setIncomingClaims(await listClaims('incoming') as Claim[]) } catch { setIncomingError(t('reports.incomingUnavailable')); setIncomingClaims([]) }
      try { setOutgoingClaims(await listClaims('outgoing') as Claim[]) } catch { setOutgoingError(t('reports.outgoingUnavailable')); setOutgoingClaims([]) }
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>
      if (axiosErr.response?.status === 401) { setLinkedUserId(null); setItems([]); return }
      setError(t('reports.loadFailed'))
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const runAction = async (itemId: number, action: 'resolve' | 'reopen' | 'delete') => {
    try {
      if (action === 'resolve') await resolveItem(itemId)
      if (action === 'reopen') await reopenItem(itemId)
      if (action === 'delete') await softDeleteItem(itemId)
      await load()
    } catch { setError(t('reports.actionFailed')) }
  }

  const shareLiveLocationForClaim = async (claimId: number) => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(async (position) => {
      await shareClaimLiveLocation(claimId, {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        ttl_minutes: 120,
      })
      await load()
    })
  }

  const summary = useMemo(() => ({
    total: items.length,
    incoming: incomingClaims.filter((c) => c.status === 'pending').length,
    outgoing: outgoingClaims.filter((c) => c.status === 'pending').length,
  }), [items, incomingClaims, outgoingClaims])

  return (
    <section className="stack">
      {loading ? <LoadingGrid count={4} /> : null}
      {error ? <p className="notice error">{error}</p> : null}

      {!loading && !linkedUserId ? (
        <SectionCard title={t('reports.connect.title')} subtitle={t('reports.profileOnly')}>
          <Link to="/profile"><button type="button">{t('new.goProfile')}</button></Link>
        </SectionCard>
      ) : null}

      {linkedUserId ? (
        <div className="reports-workspace stack">
          <div className="reports-tabs" role="tablist" aria-label="Reports workspace tabs">
            <button type="button" role="tab" aria-selected={activeTab === 'my'} className={`reports-tab ${activeTab === 'my' ? 'active' : ''}`} onClick={() => setActiveTab('my')}>
              My reports <span>{summary.total}</span>
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'incoming'} className={`reports-tab ${activeTab === 'incoming' ? 'active' : ''}`} onClick={() => setActiveTab('incoming')}>
              Incoming claims <span>{summary.incoming}</span>
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'outgoing'} className={`reports-tab ${activeTab === 'outgoing' ? 'active' : ''}`} onClick={() => setActiveTab('outgoing')}>
              Outgoing claims <span>{summary.outgoing}</span>
            </button>
          </div>

          {activeTab === 'my' ? (
            <SectionCard title={t('reports.my.title')} subtitle={t('reports.my.subtitle')}>
              {items.length === 0 ? <EmptyState title={t('board.empty.noReports')} subtitle={t('reports.my.emptySub')} action={<Link to="/new"><button type="button">{t('reports.my.create')}</button></Link>} /> : (
                <div className="grid">
                  {items.map((item) => (
                    <article key={item.id} className="card stack">
                      {item.image_path ? <img className="thumb" src={`/media/${item.image_path}`} alt={item.title} /> : <div className="thumb" aria-hidden="true" />}
                      <div className="card-head"><h3><Link to={`/items/${item.id}`}>{item.title}</Link></h3><span className={`badge ${item.status}`}>{item.status}</span></div>
                      <div className="status-row"><span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span><span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span></div>
                      <div className="actions-row">
                        {item.lifecycle === 'active' ? <button type="button" onClick={() => runAction(item.id, 'resolve')}>{t('reports.resolve')}</button> : null}
                        {item.lifecycle === 'resolved' ? <button type="button" onClick={() => runAction(item.id, 'reopen')}>{t('reports.reopen')}</button> : null}
                        {item.lifecycle !== 'deleted' ? <button className="button-danger" type="button" onClick={() => runAction(item.id, 'delete')}>{t('reports.delete')}</button> : null}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </SectionCard>
          ) : null}

          {activeTab === 'incoming' ? (
            <SectionCard title={t('reports.incomingTitle')} subtitle={t('reports.incomingSubtitle')}>
              {incomingError ? <p className="notice">{incomingError}</p> : null}
              {incomingClaims.length === 0 ? <EmptyState title={t('reports.incomingTitle')} subtitle={t('reports.incomingEmpty')} /> : (
                <div className="claim-feed">
                  {incomingClaims.map((claim) => (
                    <article key={claim.id} className="card stack">
                      <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
                      <div className="subtle">Item #{claim.target_item_id}</div>
                      {claim.status === 'pending' ? <div className="actions-row">
                        <button type="button" onClick={async () => { await claimAction(claim.id, 'approve'); await load() }}>{t('item.approve')}</button>
                        <button className="button-neutral" type="button" onClick={async () => { await claimAction(claim.id, 'reject'); await load() }}>{t('item.reject')}</button>
                        <button className="button-ghost" type="button" onClick={async () => { await claimAction(claim.id, 'complete'); await load() }}>{t('reports.markReturned')}</button>
                      </div> : null}
                    </article>
                  ))}
                </div>
              )}
            </SectionCard>
          ) : null}

          {activeTab === 'outgoing' ? (
            <SectionCard title={t('reports.outgoingTitle')} subtitle={t('reports.outgoingSubtitle')}>
              {outgoingError ? <p className="notice">{outgoingError}</p> : null}
              {outgoingClaims.length === 0 ? <EmptyState title={t('reports.outgoingTitle')} subtitle={t('reports.outgoingEmpty')} /> : (
                <div className="claim-feed">
                  {outgoingClaims.map((claim) => (
                    <article key={claim.id} className="card stack">
                      <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
                      <small className="subtle">#{claim.source_item_id} → #{claim.target_item_id}</small>
                      {claim.status === 'approved' ? (
                        <>
                          <p className="notice">{t('reports.contactsShared')}: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p>
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
                </div>
              )}
            </SectionCard>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
