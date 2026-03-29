import { useEffect, useMemo, useState } from 'react'
import { fetchAdminItems, generateLinkCode, getAuthMe, lifecycleItemAdmin, moderateItem, verifyItemAdmin } from '../api/items'
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
  const [moderationFilter, setModerationFilter] = useState('all')
  const [lifecycleFilter, setLifecycleFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)

  const loadItems = async (overrides?: { moderationFilter?: string; lifecycleFilter?: string; query?: string }) => {
    const moderationValue = overrides?.moderationFilter ?? moderationFilter
    const lifecycleValue = overrides?.lifecycleFilter ?? lifecycleFilter
    const queryValue = overrides?.query ?? query
    setItems(await fetchAdminItems({
      moderation_status: moderationValue === 'all' ? undefined : moderationValue,
      lifecycle: lifecycleValue === 'all' ? undefined : lifecycleValue,
      q: queryValue || undefined
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
        if (me.admin_access) await loadItems()
      } catch { setError('Could not verify admin access.') }
      finally { setAuthLoading(false) }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const run = async (fn: () => Promise<unknown>) => {
    try { await fn(); await loadItems() } catch { setError('Admin action failed.') }
  }

  const summary = useMemo(() => ({
    pending: items.filter((item) => item.moderation_status === 'pending').length,
    flagged: items.filter((item) => item.moderation_status === 'flagged').length,
    approved: items.filter((item) => item.moderation_status === 'approved').length,
    rejected: items.filter((item) => item.moderation_status === 'rejected').length,
  }), [items])

  const flaggedQueue = items.filter((item) => item.moderation_status === 'flagged')
  const pendingQueue = items.filter((item) => item.moderation_status === 'pending')

  return (
    <section className="stack">
      <PageHero
        title="Operations moderation console"
        subtitle="Review flagged and pending reports with queue-based workflows, verification controls, and lifecycle overrides."
        stats={[
          { label: 'Pending', value: summary.pending }, { label: 'Flagged', value: summary.flagged }, { label: 'Approved', value: summary.approved }, { label: 'Rejected', value: summary.rejected },
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
          <SectionCard title="Queue filters" subtitle={`Role: ${role || 'none'}. Narrow down high-priority reports first.`}>
            <form className="filters" onSubmit={(e) => { e.preventDefault(); void loadItems() }}>
              <label>Moderation<select value={moderationFilter} onChange={(e) => setModerationFilter(e.target.value)}><option value="all">All</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="flagged">Flagged</option></select></label>
              <label>Lifecycle<select value={lifecycleFilter} onChange={(e) => setLifecycleFilter(e.target.value)}><option value="all">All</option><option value="active">Active</option><option value="resolved">Resolved</option><option value="deleted">Deleted</option></select></label>
              <label>Search<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Title/category/location" /></label>
              <button type="submit">Load queue</button>
            </form>
          </SectionCard>

          <div className="layout-split">
            <SectionCard title="Flagged queue" subtitle="Highest-priority reports requiring review.">
              {flaggedQueue.length === 0 ? <p className="subtle">No flagged reports.</p> : flaggedQueue.map((item) => (
                <article className="card stack" key={item.id}>{item.image_path ? <img className="thumb" src={`/media/${item.image_path}`} alt={item.title} /> : null}
                  <strong>#{item.id} {item.title}</strong>
                  <div className="status-row"><span className={`badge ${item.status}`}>{item.status}</span><span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span><span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span></div>
                  <div className="actions-row"><button onClick={() => run(() => moderateItem(item.id, 'approve'))}>Approve</button><button className="button-neutral" onClick={() => run(() => moderateItem(item.id, 'reject', 'Rejected by admin'))}>Reject</button><button className="button-neutral" onClick={() => run(() => moderateItem(item.id, 'unflag'))}>Unflag</button></div>
                </article>
              ))}
            </SectionCard>

            <SectionCard title="Pending queue" subtitle="New moderation candidates.">
              {pendingQueue.length === 0 ? <p className="subtle">No pending reports.</p> : pendingQueue.map((item) => (
                <article className="card stack" key={item.id}>
                  <strong>#{item.id} {item.title}</strong>
                  <p className="subtle">{item.category} · {item.location}</p>
                  <div className="actions-row"><button onClick={() => run(() => moderateItem(item.id, 'approve'))}>Approve</button><button className="button-ghost" onClick={() => run(() => moderateItem(item.id, 'flag', 'Flagged by admin'))}>Flag</button></div>
                </article>
              ))}
            </SectionCard>
          </div>

          <SectionCard title="All filtered reports" subtitle="Full operations board with advanced controls.">
            {items.length === 0 ? <EmptyState title="No reports in this queue" subtitle="Adjust filters to widen scope." /> : (
              <div className="grid">{items.map((item) => (
                <article key={item.id} className="card stack">
                  <h3>#{item.id} {item.title}</h3>
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
              ))}</div>
            )}
          </SectionCard>
        </>
      ) : null}
    </section>
  )
}
