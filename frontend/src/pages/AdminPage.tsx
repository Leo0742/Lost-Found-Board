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
  bulkVerifyAction,
  itemLifecycleAction,
  itemModerationAction,
  itemVerifyAction,
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
    pendingQueue,
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
  const summaryCount = activePreset === 'pending'
    ? pendingQueue.length
    : activePreset === 'flagged' || activePreset === 'suspicious'
      ? flaggedQueue.length
      : items.length
  const reviewItems = activePreset === 'pending'
    ? pendingQueue
    : activePreset === 'flagged' || activePreset === 'suspicious'
      ? flaggedQueue
      : items

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
          <div className="reports-tabs admin-tabs" role="tablist" aria-label="Moderation workspace tabs">
            <button type="button" role="tab" aria-selected={activeTab === 'review'} className={`reports-tab ${activeTab === 'review' ? 'active' : ''}`} onClick={() => setActiveTab('review')}>
              Review queue <span>{summaryCount}</span>
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'reports'} className={`reports-tab ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
              Reports <span>{items.length}</span>
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'audit'} className={`reports-tab ${activeTab === 'audit' ? 'active' : ''}`} onClick={() => setActiveTab('audit')}>
              Audit log <span>{auditEvents.length}</span>
            </button>
          </div>

          {activeTab === 'review' ? (
            <SectionCard title="Review queue" subtitle={`Role: ${role || 'none'}. Fast triage with preset queues.`}>
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
                }}>Prev page</button>
                <button type="button" className="button-neutral" disabled={loadingItems} onClick={() => {
                  const next = itemsOffset + itemFilters.limit
                  setItemsOffset(next)
                  void loadItems(undefined, next)
                }}>Next page</button>
                <p className="subtle">Offset: {itemsOffset}</p>
                {loadingItems ? <p className="subtle">Loading queue…</p> : null}
              </div>
              {selectedIds.length > 0 ? (
                <div className="actions-row bulk-strip">
                  <span className="subtle">Selected: {selectedIds.length}</span>
                  <button onClick={() => canRunBulk && void runBulkAction('Bulk approve', () => bulkModerationAction(selectedIds, 'approve'))}>Bulk approve</button>
                  <button className="button-neutral" onClick={() => canRunBulk && void runBulkAction('Bulk reject', () => bulkModerationAction(selectedIds, 'reject', 'Rejected by admin'))}>Bulk reject</button>
                  <button className="button-ghost" onClick={() => canRunBulk && void runBulkAction('Bulk flag', () => bulkModerationAction(selectedIds, 'flag', 'Flagged by admin'))}>Bulk flag</button>
                  <button className="button-neutral" onClick={() => canRunBulk && void runBulkAction('Bulk unflag', () => bulkModerationAction(selectedIds, 'unflag'))}>Bulk unflag</button>
                  <button className="button-neutral" onClick={() => setSelectedIds([])}>Clear</button>
                </div>
              ) : null}
              <ModerationQueueFeed
                items={reviewItems}
                signals={signals}
                selectedIds={selectedIds}
                onToggleSelected={(id) => setSelectedIds((prev) => (selectedSet.has(id) ? prev.filter((row) => row !== id) : [...prev, id]))}
                onApprove={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'approve'))}
                onReject={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'reject', 'Rejected by admin'))}
                onFlag={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'flag', 'Flagged by admin'))}
                onUnflag={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'unflag'))}
              />
            </SectionCard>
          ) : null}

          {activeTab === 'reports' ? (
            <SectionCard title="Reports" subtitle="Browse and moderate all reports with a simpler filter workflow.">
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
                }}>Prev page</button>
                <button type="button" className="button-neutral" disabled={loadingItems} onClick={() => {
                  const next = itemsOffset + itemFilters.limit
                  setItemsOffset(next)
                  void loadItems(undefined, next)
                }}>Next page</button>
                <p className="subtle">Offset: {itemsOffset}</p>
              </div>
              {items.length === 0 ? <EmptyState title="No reports in this queue" subtitle="Adjust filters to widen scope." /> : (
                <AllReportsSection
                  items={items}
                  signals={signals}
                  role={role}
                  selectedIds={selectedIds}
                  onToggleSelected={(id) => setSelectedIds((prev) => (selectedSet.has(id) ? prev.filter((row) => row !== id) : [...prev, id]))}
                  onSelectAllVisible={() => setSelectedIds(items.map((item) => item.id))}
                  onClearSelection={() => setSelectedIds([])}
                  onBulkApprove={() => canRunBulk && void runBulkAction('Bulk approve', () => bulkModerationAction(selectedIds, 'approve'))}
                  onBulkReject={() => canRunBulk && void runBulkAction('Bulk reject', () => bulkModerationAction(selectedIds, 'reject', 'Rejected by admin'))}
                  onBulkFlag={() => canRunBulk && void runBulkAction('Bulk flag', () => bulkModerationAction(selectedIds, 'flag', 'Flagged by admin'))}
                  onBulkUnflag={() => canRunBulk && void runBulkAction('Bulk unflag', () => bulkModerationAction(selectedIds, 'unflag'))}
                  onBulkVerify={(next) => canRunBulk && role === 'admin' && void runBulkAction(next ? 'Bulk verify' : 'Bulk unverify', () => bulkVerifyAction(selectedIds, next))}
                  onBulkLifecycle={(action) => {
                    if (!canRunBulk || role !== 'admin') return
                    if (!window.confirm(`Apply ${action} to ${selectedIds.length} selected reports?`)) return
                    void runBulkAction(`Bulk ${action}`, () => bulkLifecycleAction(selectedIds, action))
                  }}
                  onApprove={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'approve'))}
                  onReject={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'reject', 'Rejected by admin'))}
                  onFlag={(id) => void runSingleItemAction(id, () => itemModerationAction(id, 'flag', 'Flagged by admin'))}
                  onVerifyToggle={(id, next) => void runSingleItemAction(id, () => itemVerifyAction(id, next))}
                  onResolve={(id) => void runSingleItemAction(id, () => itemLifecycleAction(id, 'resolve'))}
                  onReopen={(id) => void runSingleItemAction(id, () => itemLifecycleAction(id, 'reopen'))}
                  onDelete={(id) => {
                    if (!window.confirm(`Delete report #${id}?`)) return
                    void runSingleItemAction(id, () => itemLifecycleAction(id, 'delete'))
                  }}
                />
              )}
            </SectionCard>
          ) : null}

          {activeTab === 'audit' ? (
            <SectionCard title="Audit log" subtitle="Review moderation history and filter by actor/item/date.">
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
                <summary>System details</summary>
                <p className="subtle">High-risk flagged (24h): {queueSummary?.high_risk_flagged_24h ?? 0} · Stale pending (48h): {queueSummary?.stale_pending_48h ?? 0} {loadingStats ? '· Updating…' : ''}</p>
                <p className="subtle">Duplicate flags 24h: {observability?.duplicate_flags_24h ?? 0} · Duplicate claims 24h: {observability?.duplicate_claims_24h ?? 0} · Claim pressure 24h: {observability?.claims_created_24h ?? 0}</p>
                <p className="subtle">Blocked audit queries 24h: {observability?.blocked_admin_audit_queries_24h ?? 0} · Runtime: {String(observability?.semantic_runtime?.state ?? 'unknown')}</p>
                <p className="subtle">Maintenance: temp {String(observability?.cleanup?.maintenance_status?.temp_media_cleanup?.last_success_at ?? 'n/a')} · orphan {String(observability?.cleanup?.maintenance_status?.finalized_orphan_cleanup?.last_success_at ?? 'n/a')} · anti-abuse {String(observability?.cleanup?.maintenance_status?.anti_abuse_retention_cleanup?.last_success_at ?? 'n/a')} · audit {String(observability?.cleanup?.maintenance_status?.audit_retention_cleanup?.last_success_at ?? 'n/a')}</p>
                {maintenanceHealthSummary ? <p className="subtle">Maintenance health: {maintenanceHealthSummary}</p> : null}
              </details>
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
