import { AuditEvent } from '../../api/items'
import { AuditFilters } from '../../hooks/useAdminDashboard'
import { useSettings } from '../../context/SettingsContext'

type Props = {
  filters: AuditFilters
  onFiltersChange: (filters: AuditFilters) => void
  events: AuditEvent[]
  offset: number
  loading: boolean
  onApply: () => void
  onPrev: () => void
  onNext: () => void
  onFilterItem: (itemId: number) => void
  onFilterClaim: (claimId: number) => void
}

const prettifyType = (eventType: string) => eventType.replace(/_/g, ' ')

export const AuditFeedSection = ({
  filters,
  onFiltersChange,
  events,
  offset,
  loading,
  onApply,
  onPrev,
  onNext,
  onFilterItem,
  onFilterClaim,
}: Props) => {
  const { t } = useSettings()
  const patch = (key: keyof AuditFilters, value: string | number) => onFiltersChange({ ...filters, [key]: value })

  return (
    <>
      <form className="filters audit-filters" onSubmit={(e) => { e.preventDefault(); onApply() }}>
        <label className="filter-field audit-field-event">{t('admin.audit.eventType')}<input value={filters.auditType} onChange={(e) => patch('auditType', e.target.value)} placeholder="item_moderated" /></label>
        <label className="filter-field">{t('admin.audit.actor')}<input value={filters.auditActor} onChange={(e) => patch('auditActor', e.target.value)} placeholder={t('admin.audit.actorPlaceholder')} /></label>
        <label className="filter-field">{t('admin.audit.item')}<input value={filters.auditItem} onChange={(e) => patch('auditItem', e.target.value)} placeholder={t('admin.audit.itemPlaceholder')} /></label>
        <label className="filter-field">{t('admin.audit.claim')}<input value={filters.auditClaim} onChange={(e) => patch('auditClaim', e.target.value)} placeholder={t('admin.audit.claimPlaceholder')} /></label>
        <label className="filter-field">{t('admin.audit.from')}<input type="datetime-local" value={filters.auditCreatedFrom} onChange={(e) => patch('auditCreatedFrom', e.target.value)} /></label>
        <label className="filter-field">{t('admin.audit.to')}<input type="datetime-local" value={filters.auditCreatedTo} onChange={(e) => patch('auditCreatedTo', e.target.value)} /></label>
        <label className="filter-field">{t('admin.audit.limit')}<select value={filters.auditLimit} onChange={(e) => patch('auditLimit', Number(e.target.value))}><option value={20}>20</option><option value={30}>30</option><option value={50}>50</option></select></label>
        <div className="filter-actions audit-filters-actions">
          <button type="submit">{t('admin.filters.apply')}</button>
        </div>
      </form>
      <div className="actions-row">
        <button className="button-neutral" onClick={onPrev}>{t('admin.prevPage')}</button>
        <button className="button-neutral" onClick={onNext}>{t('admin.nextPage')}</button>
        <p className="subtle">{t('admin.offset', { offset })}</p>
      </div>
      {loading ? <p className="subtle">{t('admin.audit.loading')}</p> : null}
      {events.length === 0 ? <p className="subtle">{t('admin.audit.empty')}</p> : (
        <div className="timeline-list">
          {events.map((event) => (
            <article className="card timeline-item" key={event.id}>
              <strong>{event.summary || event.label || prettifyType(event.event_type)}</strong>
              <p className="subtle">{prettifyType(event.event_type)} · {new Date(event.created_at).toLocaleString()}</p>
              <p className="subtle">{t('admin.audit.meta', { actor: event.actor_telegram_user_id ?? 'n/a', item: event.item_id ?? 'n/a', claim: event.claim_id ?? 'n/a' })}</p>
              <div className="actions-row">
                {event.item_id ? <button className="button-neutral" onClick={() => event.item_id != null && onFilterItem(event.item_id)}>{t('admin.audit.filterItem', { id: event.item_id })}</button> : null}
                {event.claim_id ? <button className="button-neutral" onClick={() => event.claim_id != null && onFilterClaim(event.claim_id)}>{t('admin.audit.filterClaim', { id: event.claim_id })}</button> : null}
              </div>
              {event.details ? <p className="subtle">{t('admin.audit.details')}: {Object.entries(event.details).map(([k, v]) => `${k}=${String(v)}`).slice(0, 6).join(' · ')}</p> : null}
            </article>
          ))}
        </div>
      )}
    </>
  )
}
