import { useEffect, useMemo, useState } from 'react'
import {
  fetchAdminItems,
  fetchAuditEvents,
  fetchModerationSignals,
  fetchModerationStats,
  generateLinkCode,
  getAuthMe,
  lifecycleItemAdmin,
  moderateItem,
  verifyItemAdmin,
  type AuditEvent,
  type ModerationSignal,
  type ModerationStats,
} from '../api/items'
import { Item } from '../types/item'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'

export const AdminPage = () => {
  const [authLoading, setAuthLoading] = useState(true)
  const [linked, setLinked] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [role, setRole] = useState<'admin' | 'moderator' | null>(null)
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [signals, setSignals] = useState<Record<number, ModerationSignal>>({})
  const [stats, setStats] = useState<ModerationStats | null>(null)
  const [moderationFilter, setModerationFilter] = useState('all')
  const [lifecycleFilter, setLifecycleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [verifiedFilter, setVerifiedFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [actorFilter, setActorFilter] = useState('')
  const [query, setQuery] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [error, setError] = useState<string | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [auditType, setAuditType] = useState('')
  const [auditActor, setAuditActor] = useState('')
  const [auditItem, setAuditItem] = useState('')
  const [auditClaim, setAuditClaim] = useState('')
  const [auditOffset, setAuditOffset] = useState(0)

  const loadItems = async () => {
    const rows = await fetchAdminItems({
      moderation_status: moderationFilter === 'all' ? undefined : moderationFilter,
      lifecycle: lifecycleFilter === 'all' ? undefined : lifecycleFilter,
      status: statusFilter === 'all' ? undefined : statusFilter,
      is_verified: verifiedFilter === 'all' ? undefined : verifiedFilter === 'verified',
      category: categoryFilter || undefined,
      actor_telegram_user_id: actorFilter ? Number(actorFilter) : undefined,
      q: query || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
      limit: 200,
    })
    setItems(rows)
    const signalRows = await fetchModerationSignals(rows.map((item) => item.id))
    setSignals(Object.fromEntries(signalRows.map((row) => [row.item_id, row])))
  }

  const loadAudit = async (nextOffset: number = auditOffset) => {
    setAuditEvents(await fetchAuditEvents({
      limit: 30,
      offset: nextOffset,
      event_type: auditType || undefined,
      actor_telegram_user_id: auditActor ? Number(auditActor) : undefined,
      item_id: auditItem ? Number(auditItem) : undefined,
      claim_id: auditClaim ? Number(auditClaim) : undefined,
    }))
  }

  useEffect(() => {
    const load = async () => {
      setAuthLoading(true)
      try {
        const me = await getAuthMe()
        setLinked(me.linked)
        setLinkedUserId(me.identity?.telegram_user_id ?? null)
        setLinkedUsername(me.identity?.telegram_username ?? null)
        setRole(me.role ?? null)
        setIsAdmin(me.admin_access)
        if (me.admin_access) {
          await Promise.all([loadItems(), loadAudit(0), fetchModerationStats().then(setStats)])
        }
      } catch { setError('Could not verify admin access.') }
      finally { setAuthLoading(false) }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const run = async (fn: () => Promise<unknown>) => {
    try {
      await fn()
      await Promise.all([loadItems(), loadAudit(0), fetchModerationStats().then(setStats)])
      setAuditOffset(0)
    } catch {
      setError('Admin action failed.')
    }
  }

  const summary = useMemo(() => ({
    pending: items.filter((item) => item.moderation_status === 'pending').length,
    flagged: items.filter((item) => item.moderation_status === 'flagged').length,
    approved: items.filter((item) => item.moderation_status === 'approved').length,
    rejected: items.filter((item) => item.moderation_status === 'rejected').length,
  }), [items])

  const flaggedQueue = items.filter((item) => item.moderation_status === 'flagged').sort((a, b) => (signals[b.id]?.recent_flags_24h ?? 0) - (signals[a.id]?.recent_flags_24h ?? 0))
  const pendingQueue = items.filter((item) => item.moderation_status === 'pending')

  return (
    <section className="stack">
      <PageHero
        title="Operations moderation console"
        subtitle="Queue-first review with abuse signals, fast filters, and audit traceability."
        stats={[
          { label: 'Pending', value: stats?.pending ?? summary.pending },
          { label: 'Flagged', value: stats?.flagged ?? summary.flagged },
          { label: 'Active', value: stats?.active ?? 0 },
          { label: 'Open claims', value: stats?.unresolved_claims ?? 0 },
        ]}
      />

      {authLoading ? <LoadingGrid count={3} /> : null}
      {error ? <p className="notice error">{error}</p> : null}

      {!authLoading && !linked ? (
        <SectionCard title="Connect Telegram first" subtitle="Admin roles are bound to Telegram-linked identity.">
          <button type="button" onClick={async () => setLinkCode((await generateLinkCode()).code)}>Generate link code</button>
          {linkCode ? <p className="notice">Send this to bot: <strong>/link {linkCode}</strong></p> : null}
        </SectionCard>
      ) : null}

      {!authLoading && linked && !isAdmin ? <p className="notice error">Access denied for {linkedUsername ? `@${linkedUsername}` : linkedUserId}.</p> : null}

      {!authLoading && linked && isAdmin ? (
        <>
          <SectionCard title="Queue filters" subtitle={`Role: ${role || 'none'}. Tune by verification, actor, and sort order.`}>
            <form className="filters" onSubmit={(e) => { e.preventDefault(); void loadItems() }}>
              <label>Moderation<select value={moderationFilter} onChange={(e) => setModerationFilter(e.target.value)}><option value="all">All</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="flagged">Flagged</option></select></label>
              <label>Lifecycle<select value={lifecycleFilter} onChange={(e) => setLifecycleFilter(e.target.value)}><option value="all">All</option><option value="active">Active</option><option value="resolved">Resolved</option><option value="deleted">Deleted</option></select></label>
              <label>Status<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="all">All</option><option value="lost">Lost</option><option value="found">Found</option></select></label>
              <label>Verified<select value={verifiedFilter} onChange={(e) => setVerifiedFilter(e.target.value)}><option value="all">All</option><option value="verified">Verified only</option><option value="unverified">Unverified only</option></select></label>
              <label>Category<input value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} placeholder="Exact category" /></label>
              <label>Actor ID<input value={actorFilter} onChange={(e) => setActorFilter(e.target.value)} placeholder="Owner Telegram ID" /></label>
              <label>Search<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Title/location/contact/user" /></label>
              <label>Sort<select value={sortBy} onChange={(e) => setSortBy(e.target.value)}><option value="created_at">Created</option><option value="updated_at">Updated</option><option value="moderated_at">Moderated</option><option value="id">ID</option></select></label>
              <label>Order<select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}><option value="desc">Desc</option><option value="asc">Asc</option></select></label>
              <button type="submit">Load queue</button>
            </form>
          </SectionCard>

          <div className="layout-split">
            <SectionCard title="Flagged queue" subtitle="Prioritized by recent flag spikes.">
              {flaggedQueue.length === 0 ? <p className="subtle">No flagged reports.</p> : flaggedQueue.map((item) => {
                const signal = signals[item.id]
                return <article className="card stack" key={item.id}><strong>#{item.id} {item.title}</strong>
                  <p className="subtle">flags: {signal?.total_flags ?? 0} total · {signal?.recent_flags_24h ?? 0} in 24h · claims: {signal?.claim_count ?? 0}</p>
                  <p className="subtle">markers: {(signal?.suspicion_markers?.join(', ') || 'none')}</p>
                  <div className="actions-row"><button onClick={() => run(() => moderateItem(item.id, 'approve'))}>Approve</button><button className="button-neutral" onClick={() => run(() => moderateItem(item.id, 'reject', 'Rejected by admin'))}>Reject</button><button className="button-neutral" onClick={() => run(() => moderateItem(item.id, 'unflag'))}>Unflag</button></div>
                </article>
              })}
            </SectionCard>

            <SectionCard title="Pending queue" subtitle="Fast triage for fresh reports.">
              {pendingQueue.length === 0 ? <p className="subtle">No pending reports.</p> : pendingQueue.map((item) => (
                <article className="card stack" key={item.id}>
                  <strong>#{item.id} {item.title}</strong>
                  <p className="subtle">{item.category} · {item.location}</p>
                  <div className="actions-row"><button onClick={() => run(() => moderateItem(item.id, 'approve'))}>Approve</button><button className="button-ghost" onClick={() => run(() => moderateItem(item.id, 'flag', 'Flagged by admin'))}>Flag</button></div>
                </article>
              ))}
            </SectionCard>
          </div>

          <SectionCard title="All filtered reports" subtitle="Full moderation workspace with action groups.">
            {items.length === 0 ? <EmptyState title="No reports in this queue" subtitle="Adjust filters to widen scope." /> : (
              <div className="grid">{items.map((item) => {
                const signal = signals[item.id]
                return <article key={item.id} className="card stack">
                  <h3>#{item.id} {item.title}</h3>
                  <p className="subtle">{item.category} · {item.location} · @{item.owner_telegram_username || item.telegram_username || 'n/a'}</p>
                  <p className="subtle">flags {signal?.total_flags ?? 0} · claims {signal?.claim_count ?? 0} · recent flags {signal?.recent_flags_24h ?? 0}</p>
                  <div className="status-row"><span className={`badge ${item.status}`}>{item.status}</span><span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span><span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span></div>
                  <div className="actions-row">
                    <button onClick={() => run(() => moderateItem(item.id, 'approve'))}>Approve</button>
                    <button className="button-neutral" onClick={() => run(() => moderateItem(item.id, 'reject', 'Rejected by admin'))}>Reject</button>
                    <button className="button-ghost" onClick={() => run(() => moderateItem(item.id, 'flag', 'Flagged by admin'))}>Flag</button>
                    {role === 'admin' ? <>
                      <button onClick={() => run(() => verifyItemAdmin(item.id, !item.is_verified))}>{item.is_verified ? 'Unverify' : 'Verify'}</button>
                      <button onClick={() => run(() => lifecycleItemAdmin(item.id, 'resolve'))}>Resolve</button>
                      <button className="button-neutral" onClick={() => run(() => lifecycleItemAdmin(item.id, 'reopen'))}>Reopen</button>
                      <button className="button-danger" onClick={() => run(() => lifecycleItemAdmin(item.id, 'delete'))}>Delete</button>
                    </> : null}
                  </div>
                </article>
              })}</div>
            )}
          </SectionCard>

          <SectionCard title="Recent audit events" subtitle="Filter by actor/item/claim and paginate quickly.">
            <form className="filters" onSubmit={(e) => { e.preventDefault(); setAuditOffset(0); void loadAudit(0) }}>
              <label>Event type<input value={auditType} onChange={(e) => setAuditType(e.target.value)} placeholder="item_moderated" /></label>
              <label>Actor<input value={auditActor} onChange={(e) => setAuditActor(e.target.value)} placeholder="Telegram ID" /></label>
              <label>Item<input value={auditItem} onChange={(e) => setAuditItem(e.target.value)} placeholder="Item ID" /></label>
              <label>Claim<input value={auditClaim} onChange={(e) => setAuditClaim(e.target.value)} placeholder="Claim ID" /></label>
              <button type="submit">Apply filters</button>
            </form>
            <div className="actions-row">
              <button className="button-neutral" onClick={() => { const next = Math.max(0, auditOffset - 30); setAuditOffset(next); void loadAudit(next) }}>Prev</button>
              <button className="button-neutral" onClick={() => { const next = auditOffset + 30; setAuditOffset(next); void loadAudit(next) }}>Next</button>
              <p className="subtle">Offset: {auditOffset}</p>
            </div>
            {auditEvents.length === 0 ? <p className="subtle">No events found.</p> : (
              <div className="stack">
                {auditEvents.map((event) => (
                  <article className="card stack" key={event.id}>
                    <strong>{event.event_type}</strong>
                    <p className="subtle">actor: {event.actor_telegram_user_id ?? 'n/a'} · item: {event.item_id ?? 'n/a'} · claim: {event.claim_id ?? 'n/a'}</p>
                    <p className="subtle">{new Date(event.created_at).toLocaleString()}</p>
                    {event.details ? <pre className="subtle">{JSON.stringify(event.details, null, 2)}</pre> : null}
                  </article>
                ))}
              </div>
            )}
          </SectionCard>
        </>
      ) : null}
    </section>
  )
}
