import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchItems } from '../api/items'
import { Item, ItemStatus } from '../types/item'
import { ItemCard } from '../components/ItemCard'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'

export const HomePage = () => {
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<ItemStatus | 'all'>('all')
  const [category, setCategory] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      setItems(await fetchItems({ q, status, category }))
    } catch (err) {
      console.error('Failed to load items', err)
      setItems([])
      setError('Unable to load items right now. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onSearch = async (event: FormEvent) => {
    event.preventDefault()
    await load()
  }

  const stats = useMemo(() => ({
    total: items.length,
    lost: items.filter((item) => item.status === 'lost').length,
    found: items.filter((item) => item.status === 'found').length,
    active: items.filter((item) => item.lifecycle === 'active').length,
  }), [items])

  const latest = items.slice(0, 3)

  return (
    <section className="stack">
      <PageHero
        title="Lost & Found Workspace"
        subtitle="Report, discover, and resolve ownership with trusted workflows, richer matches, and clear lifecycle tracking."
        actions={
          <>
            <Link to="/new"><button type="button">Report an item</button></Link>
            <Link to="/my-reports"><button className="button-neutral" type="button">Open control panel</button></Link>
          </>
        }
        stats={[
          { label: 'Total reports', value: stats.total },
          { label: 'Active cases', value: stats.active },
          { label: 'Lost', value: stats.lost },
          { label: 'Found', value: stats.found },
        ]}
      />

      <div className="layout-split">
        <SectionCard title="Search board" subtitle="Find items using status and category filters.">
          <form className="filters" onSubmit={onSearch}>
            <label>Search<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Keyword, title, location" /></label>
            <label>Status
              <select value={status} onChange={(e) => setStatus(e.target.value as ItemStatus | 'all')}>
                <option value="all">All</option><option value="lost">Lost</option><option value="found">Found</option>
              </select>
            </label>
            <label>Category<input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Accessories, Electronics..." /></label>
            <button type="submit">Apply filters</button>
          </form>
          {error ? <p className="notice error" role="alert">{error}</p> : null}
        </SectionCard>

        <SectionCard title="Latest activity" subtitle="Recently posted reports across the board.">
          <div className="timeline-list">
            {latest.length === 0 ? <p className="subtle">No recent activity yet.</p> : latest.map((item) => (
              <div className="timeline-item" key={item.id}>
                <strong>#{item.id} {item.title}</strong>
                <div className="status-row">
                  <span className={`badge ${item.status}`}>{item.status}</span>
                  <span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span>
                  <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
                </div>
                <p className="subtle">{item.location} · {item.category}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Board results" subtitle="Premium card view with lifecycle and moderation readability.">
        {loading ? <LoadingGrid count={6} /> : null}
        {!loading && !error && items.length === 0 ? (
          <EmptyState title="No reports found" subtitle="Try broader filters or create the first report for this category." action={<Link to="/new"><button type="button">Create report</button></Link>} />
        ) : null}
        <div className="grid">{items.map((item) => <ItemCard key={item.id} item={item} />)}</div>
      </SectionCard>
    </section>
  )
}
