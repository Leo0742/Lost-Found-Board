import { FormEvent, useEffect, useState } from 'react'
import { fetchItems } from '../api/items'
import { Item, ItemStatus } from '../types/item'
import { ItemCard } from '../components/ItemCard'

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
      const result = await fetchItems({ q, status, category })
      setItems(result)
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
  }, [])

  const onSearch = async (event: FormEvent) => {
    event.preventDefault()
    await load()
  }

  return (
    <section>
      <h1>Campus Lost & Found</h1>
      <p className="subtle">Post and discover lost or found items quickly.</p>

      <form className="filters" onSubmit={onSearch}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by keyword or location" />
        <select value={status} onChange={(e) => setStatus(e.target.value as ItemStatus | 'all')}>
          <option value="all">All</option>
          <option value="lost">Lost</option>
          <option value="found">Found</option>
        </select>
        <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category (optional)" />
        <button type="submit">Apply</button>
      </form>

      {loading ? <p>Loading...</p> : null}
      {!loading && error ? <p role="alert">{error}</p> : null}
      {!loading && !error && items.length === 0 ? <p>No items found.</p> : null}
      <div className="grid">
        {items.map((item) => (
          <ItemCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  )
}
