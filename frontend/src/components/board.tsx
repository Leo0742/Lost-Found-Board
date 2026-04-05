import { ItemStatus } from '../types/item'
import { ItemCard } from './ItemCard'
import { Item } from '../types/item'

type SortOption = 'newest' | 'oldest' | 'title'

export const BoardToolbar = ({
  q,
  onQueryChange,
  sort,
  onSortChange,
  showFilters,
  onToggleFilters,
  hasActiveFilters,
  onClearAll,
}: {
  q: string
  onQueryChange: (value: string) => void
  sort: SortOption
  onSortChange: (value: SortOption) => void
  showFilters: boolean
  onToggleFilters: () => void
  hasActiveFilters: boolean
  onClearAll: () => void
}) => (
  <div className="board-toolbar">
    <label className="board-search">
      <span className="sr-only">Search board</span>
      <input
        value={q}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="Search title, description, category, location"
      />
    </label>
    <label className="board-sort">
      <span className="sr-only">Sort</span>
      <select value={sort} onChange={(event) => onSortChange(event.target.value as SortOption)}>
        <option value="newest">Newest first</option>
        <option value="oldest">Oldest first</option>
        <option value="title">Title A–Z</option>
      </select>
    </label>
    <button className="button-neutral" type="button" onClick={onToggleFilters} aria-expanded={showFilters}>
      {showFilters ? 'Hide filters' : 'Filters'}
    </button>
    {hasActiveFilters ? <button type="button" className="button-ghost" onClick={onClearAll}>Reset</button> : null}
    <button type="submit">Search</button>
  </div>
)

export const BoardFilters = ({
  expanded,
  status,
  onStatusChange,
  category,
  onCategoryChange,
  categories,
  location,
  onLocationChange,
  locations,
  onlyWithPhoto,
  onOnlyWithPhotoChange,
  onlyVerified,
  onOnlyVerifiedChange,
}: {
  expanded: boolean
  status: ItemStatus | 'all'
  onStatusChange: (value: string) => void
  category: string
  onCategoryChange: (value: string) => void
  categories: string[]
  location: string
  onLocationChange: (value: string) => void
  locations: string[]
  onlyWithPhoto: boolean
  onOnlyWithPhotoChange: (value: boolean) => void
  onlyVerified: boolean
  onOnlyVerifiedChange: (value: boolean) => void
}) => (
  <div className={`board-filters ${expanded ? 'expanded' : ''}`}>
    <div className="board-filters-grid">
      <label>Status
        <select value={status} onChange={(event) => onStatusChange(event.target.value)}>
          <option value="all">All</option>
          <option value="lost">Lost</option>
          <option value="found">Found</option>
        </select>
      </label>

      <label>Category
        <input
          list="board-category-options"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          placeholder="Any category"
        />
        <datalist id="board-category-options">
          {categories.map((item) => <option key={item} value={item} />)}
        </datalist>
      </label>

      <label>Location
        <input
          list="board-location-options"
          value={location}
          onChange={(event) => onLocationChange(event.target.value)}
          placeholder="Any location"
        />
        <datalist id="board-location-options">
          {locations.map((item) => <option key={item} value={item} />)}
        </datalist>
      </label>

      <label className="check-chip">
        <input type="checkbox" checked={onlyWithPhoto} onChange={(event) => onOnlyWithPhotoChange(event.target.checked)} />
        With photo
      </label>

      <label className="check-chip">
        <input type="checkbox" checked={onlyVerified} onChange={(event) => onOnlyVerifiedChange(event.target.checked)} />
        Verified
      </label>
    </div>
  </div>
)

export const ActiveFilterChips = ({
  chips,
  onClearAll,
}: {
  chips: Array<{ key: string; label: string; onClear: () => void }>
  onClearAll: () => void
}) => {
  if (chips.length === 0) return null

  return (
    <div className="active-chips" aria-label="Active filters">
      {chips.map((chip) => (
        <button type="button" className="chip" key={chip.key} onClick={chip.onClear}>
          {chip.label}
          <span aria-hidden="true">×</span>
        </button>
      ))}
      <button type="button" className="chip chip-clear" onClick={onClearAll}>Clear all</button>
    </div>
  )
}

export const BoardGrid = ({ items }: { items: Item[] }) => {
  if (!items.length) return null
  return <div className="board-grid">{items.map((item) => <ItemCard key={item.id} item={item} />)}</div>
}
