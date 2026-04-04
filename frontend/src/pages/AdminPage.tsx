import { useEffect, useState } from 'react'
import { generateLinkCode, getAuthMe } from '../api/items'
import { EmptyState, LoadingGrid, PageHero, SectionCard } from '../components/ui'
import { AdminFiltersPanel } from '../components/admin/AdminFiltersPanel'
import { AllReportsSection } from '../components/admin/AllReportsSection'
import { AuditFeedSection } from '../components/admin/AuditFeedSection'
import { FlaggedQueueSection, PendingQueueSection } from '../components/admin/AdminQueueSections'
import { QueuePresetControls } from '../components/admin/QueuePresetControls'
import {
  itemLifecycleAction,
  itemModerationAction,
  itemVerifyAction,
  useAdminDashboard,
} from '../hooks/useAdminDashboard'

export const AdminPage = () => {
  const [authLoading, setAuthLoading] = useState(true)
  const [linked, setLinked] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [role, setRole] = useState<'admin' | 'moderator' | null>(null)
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)

  const {
    items,
    signals,
    stats,
    auditEvents,
    itemFilters,
    setItemFilters,
    auditFilters,
    setAuditFilters,
    auditOffset,
    setAuditOffset,
    loadingItems,
    loadingAudit,
    error,
    setError,
    loadItems,
    loadAudit,
    loadStats,
    applyPreset,
    runModerationAction,
    summary,
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
          await Promise.all([loadItems(), loadAudit(0), loadStats()])
          setAuditOffset(0)
        }
      } catch {
        setError('Could not verify admin access.')
      } finally {
        setAuthLoading(false)
      }
    }
    void load()
  }, [loadAudit, loadItems, loadStats, setAuditOffset, setError])

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
      <PageHero
        title="Operations moderation console"
        subtitle="Queue-first review with abuse signals, fast filters, and audit traceability."
        stats={[
          { label: 'Pending', value: stats?.pending ?? summary.pending },
          { label: 'Flagged', value: stats?.flagged ?? summary.flagged },
          { label: 'Approved', value: summary.approved },
          { label: 'Rejected', value: summary.rejected },
          { label: 'Abuse blocks 24h', value: stats?.recent_abuse_blocks_24h ?? 0 },
        ]}
      />

      {authLoading ? <LoadingGrid count={3} /> : null}
      {error ? <p className="notice error">{error}</p> : null}

      {!authLoading && !linked ? (
        <SectionCard title="Connect Telegram first" subtitle="Admin roles are bound to Telegram-linked identity.">
          <button type="button" onClick={async () => setLinkCode((await generateLinkCode()).code)}>Generate link code</button>
          {linkCode ? <p className="notice">Send this to bot: <strong>/link {linkCode}</strong></p> : null}
        </SectionCard>
      ) : null}

      {!authLoading && linked && !isAdmin ? <p className="notice error">Access denied for {linkedUsername ? `@${linkedUsername}` : linkedUserId}.</p> : null}

      {!authLoading && linked && isAdmin ? (
        <>
          <SectionCard title="Quick moderation queues" subtitle={`Role: ${role || 'none'}. Use presets for fast triage.`}>
            <QueuePresetControls onApply={(preset) => void applyPreset(preset)} />
          </SectionCard>

          <SectionCard title="Queue filters" subtitle="Filter by moderation, lifecycle, actor, verification, and date range.">
            <AdminFiltersPanel filters={itemFilters} onChange={setItemFilters} onSubmit={() => void loadItems()} />
            {loadingItems ? <p className="subtle">Loading queue…</p> : null}
          </SectionCard>

          <div className="layout-split">
            <SectionCard title="Flagged queue" subtitle="Prioritized by recent pressure + abuse blocks.">
              <FlaggedQueueSection
                items={flaggedQueue}
                signals={signals}
                onApprove={(id) => void runModerationAction(() => itemModerationAction(id, 'approve'))}
                onReject={(id) => void runModerationAction(() => itemModerationAction(id, 'reject', 'Rejected by admin'))}
                onUnflag={(id) => void runModerationAction(() => itemModerationAction(id, 'unflag'))}
              />
            </SectionCard>

            <SectionCard title="Pending queue" subtitle="Fast triage for fresh reports.">
              <PendingQueueSection
                items={pendingQueue}
                onApprove={(id) => void runModerationAction(() => itemModerationAction(id, 'approve'))}
                onFlag={(id) => void runModerationAction(() => itemModerationAction(id, 'flag', 'Flagged by admin'))}
              />
            </SectionCard>
          </div>

          <SectionCard title="All filtered reports" subtitle="Full moderation workspace with grouped actions and trust indicators.">
            {items.length === 0 ? <EmptyState title="No reports in this queue" subtitle="Adjust filters to widen scope." /> : (
              <AllReportsSection
                items={items}
                signals={signals}
                role={role}
                onApprove={(id) => void runModerationAction(() => itemModerationAction(id, 'approve'))}
                onReject={(id) => void runModerationAction(() => itemModerationAction(id, 'reject', 'Rejected by admin'))}
                onFlag={(id) => void runModerationAction(() => itemModerationAction(id, 'flag', 'Flagged by admin'))}
                onVerifyToggle={(id, next) => void runModerationAction(() => itemVerifyAction(id, next))}
                onResolve={(id) => void runModerationAction(() => itemLifecycleAction(id, 'resolve'))}
                onReopen={(id) => void runModerationAction(() => itemLifecycleAction(id, 'reopen'))}
                onDelete={(id) => void runModerationAction(() => itemLifecycleAction(id, 'delete'))}
              />
            )}
          </SectionCard>

          <SectionCard title="Recent audit events" subtitle="Readable audit feed with actor/item/claim/date filters.">
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
          </SectionCard>
        </>
      ) : null}
    </section>
  )
}
