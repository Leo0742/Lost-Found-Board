import { useEffect, useMemo, useState } from 'react'
import { AxiosError } from 'axios'
import { claimAction, fetchMyItems, getAuthMe, listClaims, resolveItem, reopenItem, softDeleteItem } from '../api/items'
import { Claim, Item } from '../types/item'
import { Link } from 'react-router-dom'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'
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
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)

  const load = async () => {
    setLoading(true); setError(null); setIncomingError(null); setOutgoingError(null)
    try {
      const me = await getAuthMe()
      if (!me.linked || !me.identity?.telegram_user_id) {
        setLinkedUserId(null); setLinkedUsername(null); setItems([]); setIncomingClaims([]); setOutgoingClaims([])
        return
      }
      setLinkedUserId(me.identity.telegram_user_id)
      setLinkedUsername(me.identity.telegram_username || null)
      setItems((await fetchMyItems()).sort((a, b) => b.id - a.id))
      try { setIncomingClaims(await listClaims('incoming') as Claim[]) } catch { setIncomingError(t('reports.incomingUnavailable')); setIncomingClaims([]) }
      try { setOutgoingClaims(await listClaims('outgoing') as Claim[]) } catch { setOutgoingError(t('reports.outgoingUnavailable')); setOutgoingClaims([]) }
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>
      if (axiosErr.response?.status === 401) { setLinkedUserId(null); setLinkedUsername(null); setItems([]); return }
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

  const summary = useMemo(() => ({
    total: items.length,
    active: items.filter((i) => i.lifecycle === 'active').length,
    resolved: items.filter((i) => i.lifecycle === 'resolved').length,
    incoming: incomingClaims.filter((c) => c.status === 'pending').length,
    outgoing: outgoingClaims.filter((c) => c.status === 'pending').length,
  }), [items, incomingClaims, outgoingClaims])

  return (
    <section className="stack">
      <PageHero
        title={t('reports.title')}
        subtitle={t('reports.subtitle')}
        stats={[
          { label: t('reports.stats.reports'), value: summary.total }, { label: t('reports.stats.active'), value: summary.active }, { label: t('reports.stats.incoming'), value: summary.incoming }, { label: t('reports.stats.outgoing'), value: summary.outgoing },
        ]}
      />

      {loading ? <LoadingGrid count={4} /> : null}
      {error ? <p className="notice error">{error}</p> : null}

      {!loading && !linkedUserId ? (
        <SectionCard title={t('reports.connect.title')} subtitle={t('reports.profileOnly')}>
          <Link to="/profile"><button type="button">{t('new.goProfile')}</button></Link>
        </SectionCard>
      ) : null}

      {linkedUserId ? (
        <div className="layout-three">
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

          <SectionCard title={t('reports.incomingTitle')} subtitle={t('reports.incomingSubtitle')}>
            {incomingError ? <p className="notice">{incomingError}</p> : null}
            {incomingClaims.length === 0 ? <p className="subtle">{t('reports.incomingEmpty')}</p> : incomingClaims.map((claim) => (
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
          </SectionCard>

          <div className="stack sticky-side">
            <SectionCard title={t('reports.outgoingTitle')} subtitle={t('reports.outgoingSubtitle')}>
              {outgoingError ? <p className="notice">{outgoingError}</p> : null}
              {outgoingClaims.length === 0 ? <p className="subtle">{t('reports.outgoingEmpty')}</p> : outgoingClaims.map((claim) => (
                <article key={claim.id} className="card stack">
                  <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
                  <small className="subtle">#{claim.source_item_id} → #{claim.target_item_id}</small>
                  {claim.status === 'approved' ? <p className="notice">{t('reports.contactsShared')}: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p> : null}
                </article>
              ))}
            </SectionCard>

            <SectionCard title={t('reports.accountTitle')} subtitle={`${t('reports.signedInAs')} ${linkedUsername ? `@${linkedUsername}` : linkedUserId}`}>
              <p className="subtle">{t('reports.profileOnly')}</p><Link to="/profile"><button type="button" className="button-neutral">{t('new.goProfile')}</button></Link>
            </SectionCard>
          </div>
        </div>
      ) : null}
    </section>
  )
}
