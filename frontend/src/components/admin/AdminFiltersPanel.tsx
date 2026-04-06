import { ItemFilters } from '../../hooks/useAdminDashboard'
import { useSettings } from '../../context/SettingsContext'

type Props = {
  filters: ItemFilters
  onChange: (filters: ItemFilters) => void
  onSubmit: () => void
  compact?: boolean
}

export const AdminFiltersPanel = ({ filters, onChange, onSubmit, compact = false }: Props) => {
  const { t } = useSettings()
  const patch = (key: keyof ItemFilters, value: string | number | boolean) => onChange({ ...filters, [key]: value })

  return (
    <form className="filters admin-filters" onSubmit={(e) => { e.preventDefault(); onSubmit() }}>
      <label className="filter-field filter-field-search">{t('common.search')}<input value={filters.query} onChange={(e) => patch('query', e.target.value)} placeholder={t('admin.filters.searchPlaceholder')} /></label>
      <label className="filter-field">{t('admin.filters.moderation')}<select value={filters.moderationFilter} onChange={(e) => patch('moderationFilter', e.target.value)}><option value="all">{t('board.status.all')}</option><option value="flagged">{t('admin.filters.flaggedComplaints')}</option></select></label>
      <label className="filter-field">{t('admin.filters.lifecycle')}<select value={filters.lifecycleFilter} onChange={(e) => patch('lifecycleFilter', e.target.value)}><option value="all">{t('board.status.all')}</option><option value="active">{t('item.lifecycle.active')}</option><option value="resolved">{t('item.lifecycle.resolved')}</option><option value="deleted">{t('item.lifecycle.deleted')}</option></select></label>
      <label className="filter-field">{t('board.filter.status')}<select value={filters.statusFilter} onChange={(e) => patch('statusFilter', e.target.value)}><option value="all">{t('board.status.all')}</option><option value="lost">{t('board.status.lost')}</option><option value="found">{t('board.status.found')}</option></select></label>
      <label className="filter-field">{t('board.filter.category')}<input value={filters.categoryFilter} onChange={(e) => patch('categoryFilter', e.target.value)} placeholder={t('admin.filters.categoryPlaceholder')} /></label>
      <label className="filter-field">{t('admin.filters.sort')}<select value={filters.sortBy} onChange={(e) => patch('sortBy', e.target.value)}><option value="created_at">{t('admin.filters.sort.created')}</option><option value="updated_at">{t('admin.filters.sort.updated')}</option><option value="moderated_at">{t('admin.filters.sort.moderated')}</option><option value="id">{t('admin.filters.sort.id')}</option></select></label>
      {!compact ? (
        <>
          <label className="filter-field">{t('admin.filters.actorId')}<input value={filters.actorFilter} onChange={(e) => patch('actorFilter', e.target.value)} placeholder={t('admin.filters.actorPlaceholder')} /></label>
          <label className="filter-field">{t('admin.filters.verified')}<select value={filters.verifiedFilter} onChange={(e) => patch('verifiedFilter', e.target.value)}><option value="all">{t('board.status.all')}</option><option value="verified">{t('admin.filters.verifiedOnly')}</option><option value="unverified">{t('admin.filters.unverifiedOnly')}</option></select></label>
          <label className="filter-field">{t('admin.filters.order')}<select value={filters.sortOrder} onChange={(e) => patch('sortOrder', e.target.value)}><option value="desc">{t('admin.filters.orderDesc')}</option><option value="asc">{t('admin.filters.orderAsc')}</option></select></label>
          <label className="filter-field">{t('admin.filters.pageSize')}<select value={filters.limit} onChange={(e) => patch('limit', Number(e.target.value))}><option value={50}>50</option><option value={100}>100</option><option value={150}>150</option></select></label>
          <label className="filter-field">{t('admin.filters.suspiciousOnly')}<select value={filters.suspiciousOnly ? 'yes' : 'no'} onChange={(e) => patch('suspiciousOnly', e.target.value === 'yes')}><option value="no">{t('common.no')}</option><option value="yes">{t('common.yes')}</option></select></label>
          <label className="filter-field">{t('admin.filters.createdFrom')}<input type="datetime-local" value={filters.createdFrom} onChange={(e) => patch('createdFrom', e.target.value)} /></label>
          <label className="filter-field">{t('admin.filters.createdTo')}<input type="datetime-local" value={filters.createdTo} onChange={(e) => patch('createdTo', e.target.value)} /></label>
        </>
      ) : (
        <details className="admin-filters-advanced">
          <summary>{t('admin.filters.advanced')}</summary>
          <div className="admin-filters-advanced-grid">
            <label className="filter-field">{t('admin.filters.actorId')}<input value={filters.actorFilter} onChange={(e) => patch('actorFilter', e.target.value)} placeholder={t('admin.filters.actorPlaceholder')} /></label>
            <label className="filter-field">{t('admin.filters.verified')}<select value={filters.verifiedFilter} onChange={(e) => patch('verifiedFilter', e.target.value)}><option value="all">{t('board.status.all')}</option><option value="verified">{t('admin.filters.verifiedOnly')}</option><option value="unverified">{t('admin.filters.unverifiedOnly')}</option></select></label>
            <label className="filter-field">{t('admin.filters.order')}<select value={filters.sortOrder} onChange={(e) => patch('sortOrder', e.target.value)}><option value="desc">{t('admin.filters.orderDesc')}</option><option value="asc">{t('admin.filters.orderAsc')}</option></select></label>
            <label className="filter-field">{t('admin.filters.pageSize')}<select value={filters.limit} onChange={(e) => patch('limit', Number(e.target.value))}><option value={50}>50</option><option value={100}>100</option><option value={150}>150</option></select></label>
            <label className="filter-field">{t('admin.filters.suspiciousOnly')}<select value={filters.suspiciousOnly ? 'yes' : 'no'} onChange={(e) => patch('suspiciousOnly', e.target.value === 'yes')}><option value="no">{t('common.no')}</option><option value="yes">{t('common.yes')}</option></select></label>
            <label className="filter-field">{t('admin.filters.createdFrom')}<input type="datetime-local" value={filters.createdFrom} onChange={(e) => patch('createdFrom', e.target.value)} /></label>
            <label className="filter-field">{t('admin.filters.createdTo')}<input type="datetime-local" value={filters.createdTo} onChange={(e) => patch('createdTo', e.target.value)} /></label>
          </div>
        </details>
      )}
      <div className="filter-actions admin-filters-actions">
        <button type="submit">{compact ? t('admin.filters.apply') : t('admin.filters.loadQueue')}</button>
      </div>
    </form>
  )
}
