import { useEffect, useMemo, useState } from 'react'
import { fetchItem, reopenItem, resolveItem, softDeleteItem } from '../api/items'
import { Item } from '../types/item'
import { Link } from 'react-router-dom'

const STORAGE_KEY = 'lfb_my_report_ids'
const OWNER_KEY = 'lfb_owner_id'

const getOwnedIds = (): number[] => {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as number[]
    return parsed.filter((id) => Number.isInteger(id))
  } catch {
    return []
  }
}

const getOwnerId = (): number | null => {
  const raw = localStorage.getItem(OWNER_KEY)
  if (!raw) return null
  const id = Number(raw)
  return Number.isInteger(id) ? id : null
}

export const MyReportsPage = () => {
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const ownerId = useMemo(() => getOwnerId(), [])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const ids = getOwnedIds()
      const result = await Promise.all(ids.map((id) => fetchItem(String(id)).catch(() => null)))
      setItems(result.filter((item): item is Item => Boolean(item)).sort((a, b) => b.id - a.id))
    } catch (err) {
      console.error(err)
      setError('Failed to load your reports.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const runAction = async (itemId: number, action: 'resolve' | 'reopen' | 'delete') => {
    if (!ownerId) {
      setError('No local owner id found. Create a report from this browser first.')
      return
    }
    try {
      if (action === 'resolve') await resolveItem(itemId, ownerId)
      if (action === 'reopen') await reopenItem(itemId, ownerId)
      if (action === 'delete') await softDeleteItem(itemId, ownerId)
      await load()
    } catch (err) {
      console.error(err)
      setError('Action failed. This report may not be owned by this browser profile.')
    }
  }

  return (
    <section>
      <h1>My Reports</h1>
      <p className="subtle">Reports created from this browser profile.</p>
      {loading ? <p>Loading...</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {!loading && items.length === 0 ? <p>No reports yet. Create one from the Report Item page.</p> : null}

      <div className="grid">
        {items.map((item) => (
          <article key={item.id} className="card">
            <div className="card-head">
              <h3>
                <Link to={`/items/${item.id}`}>{item.title}</Link>
              </h3>
              <span className={`badge ${item.status}`}>{item.status}</span>
            </div>
            <p>
              Lifecycle: <strong>{item.lifecycle}</strong>
            </p>
            <div className="meta">
              <span>{item.category}</span>
              <span>{item.location}</span>
            </div>
            <div className="actions-row">
              {item.lifecycle === 'active' ? (
                <button type="button" onClick={() => runAction(item.id, 'resolve')}>Resolve</button>
              ) : null}
              {item.lifecycle === 'resolved' ? (
                <button type="button" onClick={() => runAction(item.id, 'reopen')}>Reopen</button>
              ) : null}
              {item.lifecycle !== 'deleted' ? (
                <button type="button" className="danger" onClick={() => runAction(item.id, 'delete')}>Delete</button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
