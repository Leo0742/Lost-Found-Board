import { useEffect, useState } from 'react'
import { fetchAdminItems, generateLinkCode, getAuthMe, lifecycleItemAdmin, moderateItem, verifyItemAdmin } from '../api/items'
import { Item } from '../types/item'

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
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadAccess = async () => {
    setAuthLoading(true)
    setError(null)
    try {
      const me = await getAuthMe()
      setLinked(me.linked)
      setLinkedUserId(me.identity?.telegram_user_id ?? null)
      setLinkedUsername(me.identity?.telegram_username ?? null)
      setRole(me.role ?? null)
      setIsAdmin(me.admin_access)
      if (me.admin_access) {
        await loadItems()
      } else {
        setItems([])
      }
    } catch (err) {
      console.error(err)
      setError('Could not verify admin access.')
    } finally {
      setAuthLoading(false)
    }
  }

  const loadItems = async (overrides?: { moderationFilter?: string; lifecycleFilter?: string; query?: string }) => {
    const moderationValue = overrides?.moderationFilter ?? moderationFilter
    const lifecycleValue = overrides?.lifecycleFilter ?? lifecycleFilter
    const queryValue = overrides?.query ?? query
    const data = await fetchAdminItems({
      moderation_status: moderationValue === 'all' ? undefined : moderationValue,
      lifecycle: lifecycleValue === 'all' ? undefined : lifecycleValue,
      q: queryValue || undefined
    })
    setItems(data)
  }

  const load = async () => {
    setError(null)
    try {
      if (!isAdmin) return
      setIsRefreshing(true)
      await loadItems()
    } catch (err) {
      console.error(err)
      setError('Admin data load failed. Access may be denied.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const run = async (fn: () => Promise<unknown>) => {
    try {
      await fn()
      await load()
    } catch (err) {
      console.error(err)
      setError('Admin action failed.')
    }
  }

  const applyModerationQueue = async (next: 'all' | 'pending' | 'flagged') => {
    setModerationFilter(next)
    setError(null)
    try {
      setIsRefreshing(true)
      await loadItems({ moderationFilter: next })
    } catch (err) {
      console.error(err)
      setError('Could not load selected moderation queue.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const startLinkFlow = async () => {
    try {
      const result = await generateLinkCode()
      setLinkCode(result.code)
      setError(null)
    } catch (err) {
      console.error(err)
      setError('Could not create link code right now.')
    }
  }

  useEffect(() => {
    loadAccess()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const identityLabel = linkedUsername ? `@${linkedUsername}` : linkedUserId
  const pendingCount = items.filter((item) => item.moderation_status === 'pending').length
  const flaggedCount = items.filter((item) => item.moderation_status === 'flagged').length
  const approvedCount = items.filter((item) => item.moderation_status === 'approved').length

  return (
    <section>
      <h1>Admin Moderation</h1>
      <p className="subtle">Review reported items, process moderation decisions, and keep the board trusted.</p>
      {authLoading ? <p>Checking admin access...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {!authLoading && !linked ? (
        <article className="card">
          <h3>Connect Telegram first</h3>
          <p>Admin access uses your Telegram-linked web session.</p>
          <button type="button" onClick={startLinkFlow}>Generate link code</button>
          {linkCode ? <p>Send this to bot: <strong>/link {linkCode}</strong></p> : null}
        </article>
      ) : null}

      {!authLoading && linked ? (
        <article className="card">
          <p>Signed in as: <strong>{identityLabel}</strong></p>
          {isAdmin ? (
            <p>
              Admin access granted. Role: <span className={`inline-role-badge ${role || ''}`}>{role}</span>
            </p>
          ) : (
            <p className="error">Access denied. This Telegram account is not configured as admin or moderator.</p>
          )}
        </article>
      ) : null}

      {!authLoading && linked && isAdmin ? (
        <>
          <div className="form">
            <div className="queue-shortcuts">
              <button type="button" onClick={() => applyModerationQueue('flagged')}>Flagged Queue ({flaggedCount})</button>
              <button type="button" onClick={() => applyModerationQueue('pending')}>Pending Queue ({pendingCount})</button>
              <button type="button" onClick={() => applyModerationQueue('all')}>All ({items.length})</button>
            </div>
            <div className="filters">
              <select value={moderationFilter} onChange={(e) => setModerationFilter(e.target.value)}>
                <option value="all">All moderation</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="flagged">Flagged</option>
              </select>
              <select value={lifecycleFilter} onChange={(e) => setLifecycleFilter(e.target.value)}>
                <option value="all">All lifecycle</option>
                <option value="active">Active</option>
                <option value="resolved">Resolved</option>
                <option value="deleted">Deleted</option>
              </select>
              <input placeholder="Search" value={query} onChange={(e) => setQuery(e.target.value)} />
              <button type="button" onClick={load}>{isRefreshing ? 'Loading...' : 'Load Reports'}</button>
            </div>
            <div className="admin-summary">
              <span>Pending: <strong>{pendingCount}</strong></span>
              <span>Flagged: <strong>{flaggedCount}</strong></span>
              <span>Approved: <strong>{approvedCount}</strong></span>
            </div>
            <a href="/" className="subtle">← Back to main site</a>
          </div>
          <div className="grid">
            {items.map((item) => (
              <article key={item.id} className="card">
                {item.image_path ? <img className="thumb" src={`/media/${item.image_path}`} alt={item.title} /> : null}
                <h3>#{item.id} {item.title}</h3>
                <p>{item.status.toUpperCase()} • {item.lifecycle.toUpperCase()}</p>
                <p>Moderation: <strong>{item.moderation_status}</strong></p>
                <p>Verified: <strong>{item.is_verified ? 'YES' : 'NO'}</strong></p>
                <p className="subtle">{item.category} · {item.location}</p>
                <p className="subtle">Contact: {item.contact_name} {item.telegram_username || ''}</p>
                <div className="actions-row">
                  <button type="button" onClick={() => run(() => moderateItem(item.id, 'approve'))}>Approve</button>
                  <button type="button" onClick={() => run(() => moderateItem(item.id, 'reject', 'Rejected by admin'))}>Reject</button>
                  <button type="button" onClick={() => run(() => moderateItem(item.id, 'flag', 'Flagged by admin'))}>Flag</button>
                  <button type="button" onClick={() => run(() => moderateItem(item.id, 'unflag'))}>Unflag</button>
                  {role === 'admin' ? (
                    <>
                      <button type="button" onClick={() => run(() => verifyItemAdmin(item.id, !item.is_verified))}>
                        {item.is_verified ? 'Unverify' : 'Verify'}
                      </button>
                      <button type="button" onClick={() => run(() => lifecycleItemAdmin(item.id, 'resolve'))}>Resolve</button>
                      <button type="button" onClick={() => run(() => lifecycleItemAdmin(item.id, 'reopen'))}>Reopen</button>
                      <button type="button" className="danger" onClick={() => run(() => lifecycleItemAdmin(item.id, 'delete'))}>Delete</button>
                    </>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </>
      ) : null}
    </section>
  )
}
