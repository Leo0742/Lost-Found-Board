import { FormEvent, useEffect, useMemo, useState } from 'react'
import { fetchCategories, fetchItems } from '../api/items'
import { Item, ItemStatus } from '../types/item'
import { EmptyState, LoadingGrid } from '../components/ui'
import { ActiveFilterChips, BoardFilters, BoardGrid, BoardToolbar } from '../components/board'

type SortOption = 'newest' | 'oldest' | 'title'

export const HomePage = () => {
  const [items, setItems] = useState<Item[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<ItemStatus | 'all'>('all')
  const [category, setCategory] = useState('')
  const [location, setLocation] = useState('')
  const [onlyWithPhoto, setOnlyWithPhoto] = useState(false)
  const [onlyVerified, setOnlyVerified] = useState(false)
  const [sort, setSort] = useState<SortOption>('newest')
  const [showFilters, setShowFilters] = useState(false)
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

  useEffect(() => {
    const loadCategories = async () => {
      try {
        setCategories(await fetchCategories())
      } catch (err) {
        console.error('Failed to load categories', err)
      }
    }
    loadCategories()
  }, [])

  const onSearch = async (event: FormEvent) => {
    event.preventDefault()
    await load()
  }

  const locationOptions = useMemo(() => Array.from(new Set(items.map((item) => item.location).filter(Boolean))).sort(), [items])

  const visibleItems = useMemo(() => {
    let next = [...items]

    if (location) {
      const query = location.toLowerCase()
      next = next.filter((item) => item.location.toLowerCase().includes(query))
    }

    if (onlyWithPhoto) {
      next = next.filter((item) => Boolean(item.image_path))
    }

    if (onlyVerified) {
      next = next.filter((item) => item.is_verified)
    }

    next.sort((a, b) => {
      if (sort === 'oldest') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      }
      if (sort === 'title') {
        return a.title.localeCompare(b.title)
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })

    return next
  }, [items, location, onlyWithPhoto, onlyVerified, sort])

  const activeFilters = useMemo(() => {
    const chips: Array<{ key: string; label: string; onClear: () => void }> = []

    if (status !== 'all') {
      chips.push({ key: 'status', label: status === 'lost' ? 'Lost' : 'Found', onClear: () => setStatus('all') })
    }
    if (category) {
      chips.push({ key: 'category', label: category, onClear: () => setCategory('') })
    }
    if (location) {
      chips.push({ key: 'location', label: location, onClear: () => setLocation('') })
    }
    if (onlyWithPhoto) {
      chips.push({ key: 'withPhoto', label: 'With photo', onClear: () => setOnlyWithPhoto(false) })
    }
    if (onlyVerified) {
      chips.push({ key: 'verified', label: 'Verified', onClear: () => setOnlyVerified(false) })
    }
    if (q.trim()) {
      chips.push({ key: 'query', label: `“${q.trim()}”`, onClear: () => setQ('') })
    }

    return chips
  }, [category, location, onlyVerified, onlyWithPhoto, q, status])

  const clearAllFilters = async () => {
    setQ('')
    setStatus('all')
    setCategory('')
    setLocation('')
    setOnlyWithPhoto(false)
    setOnlyVerified(false)
    setSort('newest')
    await load()
  }

  return (
    <section className="stack board-page">
      <form className="board-panel stack" onSubmit={onSearch}>
        <BoardToolbar
          q={q}
          onQueryChange={setQ}
          sort={sort}
          onSortChange={setSort}
          showFilters={showFilters}
          onToggleFilters={() => setShowFilters((value) => !value)}
          hasActiveFilters={activeFilters.length > 0}
          onClearAll={clearAllFilters}
        />

        <BoardFilters
          expanded={showFilters}
          status={status}
          onStatusChange={(value) => setStatus(value as ItemStatus | 'all')}
          category={category}
          onCategoryChange={setCategory}
          categories={categories}
          location={location}
          onLocationChange={setLocation}
          locations={locationOptions}
          onlyWithPhoto={onlyWithPhoto}
          onOnlyWithPhotoChange={setOnlyWithPhoto}
          onlyVerified={onlyVerified}
          onOnlyVerifiedChange={setOnlyVerified}
        />

        <ActiveFilterChips chips={activeFilters} onClearAll={clearAllFilters} />
        {error ? <p className="notice error" role="alert">{error}</p> : null}
      </form>

      {loading ? <LoadingGrid count={8} card /> : null}
      {!loading && !error && visibleItems.length === 0 ? (
        <EmptyState
          title={activeFilters.length > 0 ? 'No matching reports' : 'No reports yet'}
          subtitle={activeFilters.length > 0 ? 'Try adjusting filters or clearing them to explore more reports.' : 'Reports will appear here once community members publish lost or found items.'}
          action={activeFilters.length > 0 ? <button type="button" className="button-neutral" onClick={clearAllFilters}>Clear filters</button> : undefined}
        />
      ) : null}

      <BoardGrid items={visibleItems} />
    </section>
  )
}
