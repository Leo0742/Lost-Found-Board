import { useEffect, useMemo, useState } from 'react'
import { AxiosError } from 'axios'
import { claimAction, fetchMyItems, generateLinkCode, getAuthMe, listClaims, resolveItem, reopenItem, softDeleteItem, unlinkTelegram } from '../api/items'
import { Claim, Item } from '../types/item'
import { Link } from 'react-router-dom'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'

export const MyReportsPage = () => {
  const [items, setItems] = useState<Item[]>([])
  const [incomingClaims, setIncomingClaims] = useState<Claim[]>([])
  const [outgoingClaims, setOutgoingClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [incomingError, setIncomingError] = useState<string | null>(null)
  const [outgoingError, setOutgoingError] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)

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
      setLinkCode(null)
      try { setIncomingClaims(await listClaims('incoming') as Claim[]) } catch { setIncomingError('Incoming claims unavailable.'); setIncomingClaims([]) }
      try { setOutgoingClaims(await listClaims('outgoing') as Claim[]) } catch { setOutgoingError('Outgoing claims unavailable.'); setOutgoingClaims([]) }
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>
      if (axiosErr.response?.status === 401) { setLinkedUserId(null); setLinkedUsername(null); setItems([]); return }
      setError('Failed to load dashboard. Please try again.')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const runAction = async (itemId: number, action: 'resolve' | 'reopen' | 'delete') => {
    try {
      if (action === 'resolve') await resolveItem(itemId)
      if (action === 'reopen') await reopenItem(itemId)
      if (action === 'delete') await softDeleteItem(itemId)
      await load()
    } catch { setError('Action failed. Ensure this Telegram-linked account owns the report.') }
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
        title="Report control panel"
        subtitle="Manage lifecycle states, inbound claims, outbound claim requests, and account linking from a dashboard workspace."
        stats={[
          { label: 'Reports', value: summary.total }, { label: 'Active', value: summary.active }, { label: 'Incoming pending', value: summary.incoming }, { label: 'Outgoing pending', value: summary.outgoing },
        ]}
      />

      {loading ? <LoadingGrid count={4} /> : null}
      {error ? <p className="notice error">{error}</p> : null}

      {!loading && !linkedUserId ? (
        <SectionCard title="Connect Telegram" subtitle="Required for secure ownership and synced web/bot workflows.">
          <button type="button" onClick={async () => setLinkCode((await generateLinkCode()).code)}>Generate link code</button>
          {linkCode ? <p className="notice">Send this in Telegram: <strong>/link {linkCode}</strong></p> : null}
        </SectionCard>
      ) : null}

      {linkedUserId ? (
        <div className="layout-three">
          <SectionCard title="My reports" subtitle="Your owned report inventory and lifecycle actions.">
            {items.length === 0 ? <EmptyState title="No reports yet" subtitle="Create a report to begin tracking lifecycle and claims." action={<Link to="/new"><button type="button">Create report</button></Link>} /> : (
              <div className="grid">
                {items.map((item) => (
                  <article key={item.id} className="card stack">
                    {item.image_path ? <img className="thumb" src={`/media/${item.image_path}`} alt={item.title} /> : <div className="thumb" aria-hidden="true" />}
                    <div className="card-head"><h3><Link to={`/items/${item.id}`}>{item.title}</Link></h3><span className={`badge ${item.status}`}>{item.status}</span></div>
                    <div className="status-row"><span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span><span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span></div>
                    <div className="actions-row">
                      {item.lifecycle === 'active' ? <button type="button" onClick={() => runAction(item.id, 'resolve')}>Resolve</button> : null}
                      {item.lifecycle === 'resolved' ? <button type="button" onClick={() => runAction(item.id, 'reopen')}>Reopen</button> : null}
                      {item.lifecycle !== 'deleted' ? <button className="button-danger" type="button" onClick={() => runAction(item.id, 'delete')}>Delete</button> : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Incoming claims" subtitle="Requests awaiting your decision.">
            {incomingError ? <p className="notice">{incomingError}</p> : null}
            {incomingClaims.length === 0 ? <p className="subtle">No incoming claims.</p> : incomingClaims.map((claim) => (
              <article key={claim.id} className="card stack">
                <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
                <div className="subtle">Item #{claim.target_item_id}</div>
                {claim.status === 'pending' ? <div className="actions-row">
                  <button type="button" onClick={async () => { await claimAction(claim.id, 'approve'); await load() }}>Approve</button>
                  <button className="button-neutral" type="button" onClick={async () => { await claimAction(claim.id, 'reject'); await load() }}>Reject</button>
                  <button className="button-ghost" type="button" onClick={async () => { await claimAction(claim.id, 'complete'); await load() }}>Mark returned</button>
                </div> : null}
              </article>
            ))}
          </SectionCard>

          <div className="stack sticky-side">
            <SectionCard title="Outgoing claims" subtitle="Claims you initiated on matched items.">
              {outgoingError ? <p className="notice">{outgoingError}</p> : null}
              {outgoingClaims.length === 0 ? <p className="subtle">No outgoing claims.</p> : outgoingClaims.map((claim) => (
                <article key={claim.id} className="card stack">
                  <div className="meta"><strong>Claim #{claim.id}</strong><span className={`badge ${claim.status === 'pending' ? 'pending' : 'approved'}`}>{claim.status}</span></div>
                  <small className="subtle">#{claim.source_item_id} → #{claim.target_item_id}</small>
                  {claim.status === 'approved' ? <p className="notice">Contacts shared: {claim.shared_source_contact || '-'} / {claim.shared_target_contact || '-'}</p> : null}
                </article>
              ))}
            </SectionCard>

            <SectionCard title="Connected account" subtitle={`Signed in as ${linkedUsername ? `@${linkedUsername}` : linkedUserId}`}>
              <button type="button" className="button-danger" onClick={async () => { await unlinkTelegram(); await load() }}>Unlink Telegram</button>
            </SectionCard>
          </div>
        </div>
      ) : null}
    </section>
  )
}
