import { useState } from 'react'
import { fetchAdminItems, lifecycleItemAdmin, moderateItem, verifyItemAdmin } from '../api/items'
import { Item } from '../types/item'

export const AdminPage = () => {
  const [secret, setSecret] = useState('')
  const [items, setItems] = useState<Item[]>([])
  const [moderationFilter, setModerationFilter] = useState('all')
  const [lifecycleFilter, setLifecycleFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setError(null)
    try {
      const data = await fetchAdminItems(secret, {
        moderation_status: moderationFilter === 'all' ? undefined : moderationFilter,
        lifecycle: lifecycleFilter === 'all' ? undefined : lifecycleFilter,
        q: query || undefined
      })
      setItems(data)
    } catch (err) {
      console.error(err)
      setError('Admin access denied or request failed.')
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

  return (
    <section>
      <h1>Admin Moderation</h1>
      <div className="form">
        <label>
          Admin secret
          <input type="password" value={secret} onChange={(e) => setSecret(e.target.value)} />
        </label>
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
          <button type="button" onClick={load}>Load Reports</button>
        </div>
      </div>
      {error ? <p className="error">{error}</p> : null}
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
              <button type="button" onClick={() => run(() => moderateItem(secret, item.id, 'approve'))}>Approve</button>
              <button type="button" onClick={() => run(() => moderateItem(secret, item.id, 'reject', 'Rejected by admin'))}>Reject</button>
              <button type="button" onClick={() => run(() => moderateItem(secret, item.id, 'flag', 'Flagged by admin'))}>Flag</button>
              <button type="button" onClick={() => run(() => moderateItem(secret, item.id, 'unflag'))}>Unflag</button>
              <button type="button" onClick={() => run(() => verifyItemAdmin(secret, item.id, !item.is_verified))}>
                {item.is_verified ? 'Unverify' : 'Verify'}
              </button>
              <button type="button" onClick={() => run(() => lifecycleItemAdmin(secret, item.id, 'resolve'))}>Resolve</button>
              <button type="button" onClick={() => run(() => lifecycleItemAdmin(secret, item.id, 'reopen'))}>Reopen</button>
              <button type="button" className="danger" onClick={() => run(() => lifecycleItemAdmin(secret, item.id, 'delete'))}>Delete</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
