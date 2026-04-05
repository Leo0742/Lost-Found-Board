import { ItemStatus } from '../types/item'
import { ItemCard } from './ItemCard'
import { Item } from '../types/item'
import { useSettings } from '../context/SettingsContext'

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
}) => {
  const { t } = useSettings()

  return (
    <div className="board-toolbar">
      <label className="board-search">
        <span className="sr-only">{t('board.searchLabel')}</span>
        <input
          value={q}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={t('board.searchPlaceholder')}
        />
      </label>
      <label className="board-sort">
        <span className="sr-only">{t('board.sort')}</span>
        <select value={sort} onChange={(event) => onSortChange(event.target.value as SortOption)}>
          <option value="newest">{t('board.sort.newest')}</option>
          <option value="oldest">{t('board.sort.oldest')}</option>
          <option value="title">{t('board.sort.title')}</option>
        </select>
      </label>
      <button className="button-neutral" type="button" onClick={onToggleFilters} aria-expanded={showFilters}>
        {showFilters ? t('common.hideFilters') : t('common.filters')}
      </button>
      {hasActiveFilters ? <button type="button" className="button-ghost" onClick={onClearAll}>{t('common.reset')}</button> : null}
      <button type="submit">{t('common.search')}</button>
    </div>
  )
}

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
}) => {
  const { t } = useSettings()

  return (
    <div className={`board-filters ${expanded ? 'expanded' : ''}`}>
      <div className="board-filters-grid">
        <label>{t('board.filter.status')}
          <select value={status} onChange={(event) => onStatusChange(event.target.value)}>
            <option value="all">{t('board.status.all')}</option>
            <option value="lost">{t('board.status.lost')}</option>
            <option value="found">{t('board.status.found')}</option>
          </select>
        </label>

        <label>{t('board.filter.category')}
          <input
            list="board-category-options"
            value={category}
            onChange={(event) => onCategoryChange(event.target.value)}
            placeholder={t('board.filter.categoryAny')}
          />
          <datalist id="board-category-options">
            {categories.map((item) => <option key={item} value={item} />)}
          </datalist>
        </label>

        <label>{t('board.filter.location')}
          <input
            list="board-location-options"
            value={location}
            onChange={(event) => onLocationChange(event.target.value)}
            placeholder={t('board.filter.locationAny')}
          />
          <datalist id="board-location-options">
            {locations.map((item) => <option key={item} value={item} />)}
          </datalist>
        </label>

        <label className="check-chip">
          <input type="checkbox" checked={onlyWithPhoto} onChange={(event) => onOnlyWithPhotoChange(event.target.checked)} />
          {t('board.filter.withPhoto')}
        </label>

        <label className="check-chip">
          <input type="checkbox" checked={onlyVerified} onChange={(event) => onOnlyVerifiedChange(event.target.checked)} />
          {t('board.filter.verified')}
        </label>
      </div>
    </div>
  )
}

export const ActiveFilterChips = ({
  chips,
  onClearAll,
}: {
  chips: Array<{ key: string; label: string; onClear: () => void }>
  onClearAll: () => void
}) => {
  const { t } = useSettings()

  if (chips.length === 0) return null

  return (
    <div className="active-chips" aria-label="Active filters">
      {chips.map((chip) => (
        <button type="button" className="chip" key={chip.key} onClick={chip.onClear}>
          {chip.label}
          <span aria-hidden="true">×</span>
        </button>
      ))}
      <button type="button" className="chip chip-clear" onClick={onClearAll}>{t('common.clearAll')}</button>
    </div>
  )
}

export const BoardGrid = ({ items }: { items: Item[] }) => {
  if (!items.length) return null
  return <div className="board-grid">{items.map((item) => <ItemCard key={item.id} item={item} />)}</div>
}
