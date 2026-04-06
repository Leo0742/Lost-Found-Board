import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAuthMe } from '../api/items'
import { EmptyState, LoadingGrid, SectionCard } from '../components/ui'
import { AdminFiltersPanel } from '../components/admin/AdminFiltersPanel'
import { AllReportsSection } from '../components/admin/AllReportsSection'
import { AuditFeedSection } from '../components/admin/AuditFeedSection'
import { ModerationQueueFeed } from '../components/admin/AdminQueueSections'
import { useSettings } from '../context/SettingsContext'
import { QueuePresetControls } from '../components/admin/QueuePresetControls'
import {
  bulkLifecycleAction,
  bulkModerationAction,
  itemLifecycleAction,
  itemModerationAction,
  useAdminDashboard,
} from '../hooks/useAdminDashboard'

export const AdminPage = () => {
  const { t } = useSettings()
  const [authLoading, setAuthLoading] = useState(true)
  const [linked, setLinked] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [role, setRole] = useState<'admin' | 'moderator' | null>(null)
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [activeTab, setActiveTab] = useState<'review' | 'reports' | 'audit'>('review')
  const [showSystemDetails, setShowSystemDetails] = useState(false)

  const {
    items,
    signals,
    queueSummary,
    observability,
    auditEvents,
    itemFilters,
    setItemFilters,
    auditFilters,
    setAuditFilters,
    itemsOffset,
    setItemsOffset,
    auditOffset,
    setAuditOffset,
    loadingItems,
    loadingAudit,
    loadingStats,
    actionLoading,
    itemError,
    signalError,
    auditError,
    statsError,
    queueSummaryError,
    observabilityError,
    actionMessage,
    actionWarning,
    setActionMessage,
    loadItems,
    loadAudit,
    refreshAll,
    applyPreset,
    activePreset,
    runSingleItemAction,
    runBulkAction,
    flaggedQueue,
  } = useAdminDashboard()

  useEffect(() => {
    const load = async () => {
      setAuthLoading(true)
      try {
        const me = await getAuthMe()
        setLinked(me.linked)
        setLinkedUserId(me.identity?.telegram_user_id ?? null)
        setLinkedUsername(me.identity?.telegram_username ?? null)
        setRole(me.role ?? null)
        setIsAdmin(me.admin_access)
        if (me.admin_access) {
          await refreshAll()
        }
      } catch {
        setActionMessage(t('admin.verifyFailed'))
      } finally {
        setAuthLoading(false)
      }
    }
    void load()
  }, [refreshAll, setActionMessage])

  useEffect(() => {
    setSelectedIds((prev) => prev.filter((id) => items.some((item) => item.id === id)))
  }, [items])

  const maintenanceRows = Object.entries(observability?.cleanup?.maintenance_status ?? {})
  const maintenanceHealthSummary = maintenanceRows
    .map(([step, status]) => `${step}:${String(status.health ?? 'unknown')}`)
    .join(' · ')

  const selectedSet = new Set(selectedIds)
  const canRunBulk = selectedIds.length > 0 && !actionLoading
  const selectedFlaggedIds = selectedIds.filter((id) => items.some((item) => item.id === id && item.moderation_status === 'flagged'))
  const summaryCount = flaggedQueue.length
  const reviewItems = flaggedQueue

  const applyAuditFilters = async () => {
    setAuditOffset(0)
    await loadAudit(0)
  }

  const filterByItem = async (itemId: number) => {
    const next = { ...auditFilters, auditItem: String(itemId) }
    setAuditFilters(next)
    setAuditOffset(0)
    await loadAudit(0, next)
  }

  const filterByClaim = async (claimId: number) => {
    const next = { ...auditFilters, auditClaim: String(claimId) }
    setAuditFilters(next)
    setAuditOffset(0)
    await loadAudit(0, next)
  }

  return (
    <section className="stack">
      {authLoading ? <LoadingGrid count={3} /> : null}
      {actionMessage ? <p className="notice">{actionMessage}</p> : null}
      {actionWarning ? <p className="notice">{t('admin.partialWarning')}: {actionWarning}</p> : null}
      {itemError ? <p className="notice error">{itemError}</p> : null}
      {signalError ? <p className="notice">{signalError}</p> : null}
      {auditError ? <p className="notice error">{auditError}</p> : null}
      {statsError ? <p className="notice error">{statsError}</p> : null}
      {queueSummaryError ? <p className="notice error">{queueSummaryError}</p> : null}
      {observabilityError ? <p className="notice error">{observabilityError}</p> : null}

      {!authLoading && !linked ? (
        <SectionCard title={t('admin.connectFirst')} subtitle={t('reports.profileOnly')}>
          <Link to="/profile"><button type="button">{t('new.goProfile')}</button></Link>
        </SectionCard>
      ) : null}

      {!authLoading && linked && !isAdmin ? <p className="notice error">{t('admin.accessDenied')} {linkedUsername ? `@${linkedUsername}` : linkedUserId}.</p> : null}

      {!authLoading && linked && isAdmin ? (
        <>
          <div className="reports-tabs admin-tabs" role="tablist" aria-label={t('admin.tabs.label')}>
            <button type="button" role="tab" aria-selected={activeTab === 'review'} className={`reports-tab ${activeTab === 'review' ? 'active' : ''}`} onClick={() => setActiveTab('review')}>
              {t('admin.tab.review')} <span>{summaryCount}</span>
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'reports'} className={`reports-tab ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
              {t('admin.tab.reports')} <span>{items.length}</span>
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'audit'} className={`reports-tab ${activeTab === 'audit' ? 'active' : ''}`} onClick={() => setActiveTab('audit')}>
              {t('admin.tab.audit')} <span>{auditEvents.length}</span>
            </button>
          </div>

          {activeTab === 'review' ? (
            <SectionCard title={t('admin.review.title')} subtitle={t('admin.review.subtitle', { role: role ? t(`role.${role}`) : t('admin.role.none') })}>
              <QueuePresetControls
                activePreset={activePreset}
                disabled={loadingItems}
                onApply={(preset) => {
                  setSelectedIds([])
                  void applyPreset(preset)
                }}
              />
              <div className="actions-row">
                <button type="button" className="button-neutral" disabled={loadingItems || itemsOffset === 0} onClick={() => {
                  const next = Math.max(0, itemsOffset - itemFilters.limit)
                  setItemsOffset(next)
                  void loadItems(undefined, next)
                }}>{t('admin.prevPage')}</button>
                <button type="button" className="button-neutral" disabled={loadingItems} onClick={() => {
                  const next = itemsOffset + itemFilters.limit
                  setItemsOffset(next)
                  void loadItems(undefined, next)
                }}>{t('admin.nextPage')}</button>
                <p className="subtle">{t('admin.offset', { offset: itemsOffset })}</p>
                {loadingItems ? <p className="subtle">{t('admin.loadingQueue')}</p> : null}
              </div>
              {selectedIds.length > 0 ? (
                <div className="actions-row bulk-strip">
                  <span className="subtle">{t('admin.selectedCount', { count: selectedIds.length })}</span>
                  <button className="button-neutral" onClick={() => selectedFlaggedIds.length > 0 && void runBulkAction(t('admin.action.bulkIgnoreComplaint'), () => bulkModerationAction(selectedFlaggedIds, 'unflag'))} disabled={selectedFlaggedIds.length === 0}>{t('admin.action.ignoreComplaintSelected')}</button>
                  {role === 'admin' ? (
                    <button className="button-danger" onClick={() => {
                      if (!window.confirm(t('admin.confirm.deleteSelected', { count: selectedIds.length }))) return
                      void runBulkAction(t('admin.action.bulkDelete'), () => bulkLifecycleAction(selectedIds, 'delete'))
                    }}>{t('admin.action.deletePostSelected')}</button>
                  ) : null}
                  <button className="button-neutral" onClick={() => setSelectedIds([])}>{t('admin.clearSelection')}</button>
                </div>
              ) : null}
              <ModerationQueueFeed
                items={reviewItems}
                signals={signals}
                selectedIds={selectedIds}
                onToggleSelected={(id) => setSelectedIds((prev) => (selectedSet.has(id) ? prev.filter((row) => row !== id) : [...prev, id]))}
                canDelete={role === 'admin'}
                onIgnoreComplaint={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'unflag'))}
                onDelete={(id) => {
                  if (!window.confirm(t('admin.confirm.deletePost', { id }))) return
                  void runSingleItemAction(id, () => itemLifecycleAction(id, 'delete'))
                }}
              />
            </SectionCard>
          ) : null}

          {activeTab === 'reports' ? (
            <SectionCard title={t('admin.reports.title')} subtitle={t('admin.reports.subtitle')}>
              <AdminFiltersPanel
                compact
                filters={itemFilters}
                onChange={(next) => {
                  setItemFilters(next)
                  setItemsOffset(0)
                }}
                onSubmit={() => void loadItems(undefined, 0)}
              />
              <div className="actions-row">
                <button type="button" className="button-neutral" disabled={loadingItems || itemsOffset === 0} onClick={() => {
                  const next = Math.max(0, itemsOffset - itemFilters.limit)
                  setItemsOffset(next)
                  void loadItems(undefined, next)
                }}>{t('admin.prevPage')}</button>
                <button type="button" className="button-neutral" disabled={loadingItems} onClick={() => {
                  const next = itemsOffset + itemFilters.limit
                  setItemsOffset(next)
                  void loadItems(undefined, next)
                }}>{t('admin.nextPage')}</button>
                <p className="subtle">{t('admin.offset', { offset: itemsOffset })}</p>
              </div>
              {items.length === 0 ? <EmptyState title={t('admin.reports.emptyTitle')} subtitle={t('admin.reports.emptySubtitle')} /> : (
                <AllReportsSection
                  items={items}
                  signals={signals}
                  role={role}
                  selectedIds={selectedIds}
                  onToggleSelected={(id) => setSelectedIds((prev) => (selectedSet.has(id) ? prev.filter((row) => row !== id) : [...prev, id]))}
                  onSelectAllVisible={() => setSelectedIds(items.map((item) => item.id))}
                  onClearSelection={() => setSelectedIds([])}
                  onBulkIgnoreComplaints={() => selectedFlaggedIds.length > 0 && void runBulkAction(t('admin.action.bulkIgnoreComplaint'), () => bulkModerationAction(selectedFlaggedIds, 'unflag'))}
                  onBulkDelete={() => {
                    if (!canRunBulk || role !== 'admin') return
                    if (!window.confirm(t('admin.confirm.deleteSelected', { count: selectedIds.length }))) return
                    void runBulkAction(t('admin.action.bulkDelete'), () => bulkLifecycleAction(selectedIds, 'delete'))
                  }}
                  onIgnoreComplaint={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'unflag'))}
                  onDelete={(id) => {
                    if (!window.confirm(t('admin.confirm.deletePost', { id }))) return
                    void runSingleItemAction(id, () => itemLifecycleAction(id, 'delete'))
                  }}
                />
              )}
            </SectionCard>
          ) : null}

          {activeTab === 'audit' ? (
            <SectionCard title={t('admin.audit.title')} subtitle={t('admin.audit.subtitle')}>
              <AuditFeedSection
                filters={auditFilters}
                onFiltersChange={setAuditFilters}
                events={auditEvents}
                offset={auditOffset}
                loading={loadingAudit}
                onApply={() => void applyAuditFilters()}
                onPrev={() => {
                  const next = Math.max(0, auditOffset - auditFilters.auditLimit)
                  setAuditOffset(next)
                  void loadAudit(next)
                }}
                onNext={() => {
                  const next = auditOffset + auditFilters.auditLimit
                  setAuditOffset(next)
                  void loadAudit(next)
                }}
                onFilterItem={(itemId) => void filterByItem(itemId)}
                onFilterClaim={(claimId) => void filterByClaim(claimId)}
              />
              <details className="admin-system-details" open={showSystemDetails} onToggle={(e) => setShowSystemDetails((e.currentTarget as HTMLDetailsElement).open)}>
                <summary>{t('admin.systemDetails')}</summary>
                <p className="subtle">{t('admin.system.highRisk', { count: queueSummary?.high_risk_flagged_24h ?? 0 })} · {t('admin.system.stale', { count: queueSummary?.stale_pending_48h ?? 0 })} {loadingStats ? `· ${t('admin.system.updating')}` : ''}</p>
                <p className="subtle">{t('admin.system.dupFlags', { count: observability?.duplicate_flags_24h ?? 0 })} · {t('admin.system.dupClaims', { count: observability?.duplicate_claims_24h ?? 0 })} · {t('admin.system.claimPressure', { count: observability?.claims_created_24h ?? 0 })}</p>
                <p className="subtle">{t('admin.system.blockedQueries', { count: observability?.blocked_admin_audit_queries_24h ?? 0 })} · {t('admin.system.runtime', { state: String(observability?.semantic_runtime?.state ?? t('admin.unknown')) })}</p>
                <p className="subtle">{t('admin.system.maintenance')}: temp {String(observability?.cleanup?.maintenance_status?.temp_media_cleanup?.last_success_at ?? 'n/a')} · orphan {String(observability?.cleanup?.maintenance_status?.finalized_orphan_cleanup?.last_success_at ?? 'n/a')} · anti-abuse {String(observability?.cleanup?.maintenance_status?.anti_abuse_retention_cleanup?.last_success_at ?? 'n/a')} · audit {String(observability?.cleanup?.maintenance_status?.audit_retention_cleanup?.last_success_at ?? 'n/a')}</p>
                {maintenanceHealthSummary ? <p className="subtle">{t('admin.system.maintenanceHealth')}: {maintenanceHealthSummary}</p> : null}
              </details>
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
