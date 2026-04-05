import { ItemFilters } from '../../hooks/useAdminDashboard'

type Props = {
  filters: ItemFilters
  onChange: (filters: ItemFilters) => void
  onSubmit: () => void
}

export const AdminFiltersPanel = ({ filters, onChange, onSubmit }: Props) => {
  const patch = (key: keyof ItemFilters, value: string | number | boolean) => onChange({ ...filters, [key]: value })

  return (
    <form className="filters admin-filters" onSubmit={(e) => { e.preventDefault(); onSubmit() }}>
      <label className="filter-field">Moderation<select value={filters.moderationFilter} onChange={(e) => patch('moderationFilter', e.target.value)}><option value="all">All</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="flagged">Flagged</option></select></label>
      <label className="filter-field">Lifecycle<select value={filters.lifecycleFilter} onChange={(e) => patch('lifecycleFilter', e.target.value)}><option value="all">All</option><option value="active">Active</option><option value="resolved">Resolved</option><option value="deleted">Deleted</option></select></label>
      <label className="filter-field">Status<select value={filters.statusFilter} onChange={(e) => patch('statusFilter', e.target.value)}><option value="all">All</option><option value="lost">Lost</option><option value="found">Found</option></select></label>
      <label className="filter-field">Verified<select value={filters.verifiedFilter} onChange={(e) => patch('verifiedFilter', e.target.value)}><option value="all">All</option><option value="verified">Verified only</option><option value="unverified">Unverified only</option></select></label>
      <label className="filter-field">Category<input value={filters.categoryFilter} onChange={(e) => patch('categoryFilter', e.target.value)} placeholder="Exact category" /></label>
      <label className="filter-field">Actor ID<input value={filters.actorFilter} onChange={(e) => patch('actorFilter', e.target.value)} placeholder="Owner Telegram ID" /></label>
      <label className="filter-field filter-field-wide">Search<input value={filters.query} onChange={(e) => patch('query', e.target.value)} placeholder="Title/location/contact/user" /></label>
      <label className="filter-field">Created from<input type="datetime-local" value={filters.createdFrom} onChange={(e) => patch('createdFrom', e.target.value)} /></label>
      <label className="filter-field">Created to<input type="datetime-local" value={filters.createdTo} onChange={(e) => patch('createdTo', e.target.value)} /></label>
      <label className="filter-field">Sort<select value={filters.sortBy} onChange={(e) => patch('sortBy', e.target.value)}><option value="created_at">Created</option><option value="updated_at">Updated</option><option value="moderated_at">Moderated</option><option value="id">ID</option></select></label>
      <label className="filter-field">Order<select value={filters.sortOrder} onChange={(e) => patch('sortOrder', e.target.value)}><option value="desc">Desc</option><option value="asc">Asc</option></select></label>
      <label className="filter-field">Page size<select value={filters.limit} onChange={(e) => patch('limit', Number(e.target.value))}><option value={50}>50</option><option value={100}>100</option><option value={150}>150</option></select></label>
      <label className="filter-field">Suspicious only<select value={filters.suspiciousOnly ? 'yes' : 'no'} onChange={(e) => patch('suspiciousOnly', e.target.value === 'yes')}><option value="no">No</option><option value="yes">Yes</option></select></label>
      <div className="filter-actions">
        <button type="submit">Load queue</button>
      </div>
    </form>
  )
}
