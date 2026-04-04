import { useCallback, useMemo, useState } from 'react'
import {
  bulkLifecycleItems,
  bulkModerateItems,
  bulkVerifyItems,
  fetchAdminItems,
  fetchAdminObservability,
  fetchAdminQueueSummary,
  fetchAuditEvents,
  fetchModerationSignals,
  fetchModerationStats,
  lifecycleItemAdmin,
  moderateItem,
  verifyItemAdmin,
  type AdminObservability,
  type AdminQueueSummary,
  type AuditEvent,
  type BulkActionResponse,
  type ModerationSignal,
  type ModerationStats,
} from '../api/items'
import { Item } from '../types/item'

export type QueuePreset = 'flagged' | 'pending' | 'recent' | 'suspicious'

export type ItemFilters = {
  moderationFilter: string
  lifecycleFilter: string
  statusFilter: string
  verifiedFilter: string
  categoryFilter: string
  actorFilter: string
  query: string
  sortBy: string
  sortOrder: string
  createdFrom: string
  createdTo: string
  limit: number
  suspiciousOnly: boolean
}

export type AuditFilters = {
  auditType: string
  auditActor: string
  auditItem: string
  auditClaim: string
  auditCreatedFrom: string
  auditCreatedTo: string
  auditLimit: number
}

const defaultItemFilters: ItemFilters = {
  moderationFilter: 'all',
  lifecycleFilter: 'all',
  statusFilter: 'all',
  verifiedFilter: 'all',
  categoryFilter: '',
  actorFilter: '',
  query: '',
  sortBy: 'created_at',
  sortOrder: 'desc',
  createdFrom: '',
  createdTo: '',
  limit: 100,
  suspiciousOnly: false,
}

const defaultAuditFilters: AuditFilters = {
  auditType: '',
  auditActor: '',
  auditItem: '',
  auditClaim: '',
  auditCreatedFrom: '',
  auditCreatedTo: '',
  auditLimit: 30,
}

export const useAdminDashboard = () => {
  const [items, setItems] = useState<Item[]>([])
  const [signals, setSignals] = useState<Record<number, ModerationSignal>>({})
  const [stats, setStats] = useState<ModerationStats | null>(null)
  const [queueSummary, setQueueSummary] = useState<AdminQueueSummary | null>(null)
  const [observability, setObservability] = useState<AdminObservability | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [itemFilters, setItemFilters] = useState<ItemFilters>(defaultItemFilters)
  const [auditFilters, setAuditFilters] = useState<AuditFilters>(defaultAuditFilters)
  const [itemsOffset, setItemsOffset] = useState(0)
  const [auditOffset, setAuditOffset] = useState(0)
  const [loadingItems, setLoadingItems] = useState(false)
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [itemError, setItemError] = useState<string | null>(null)
  const [auditError, setAuditError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const loadItems = useCallback(async (nextFilters?: ItemFilters, nextOffset?: number) => {
    const effectiveFilters = nextFilters ?? itemFilters
    const effectiveOffset = nextOffset ?? itemsOffset
    setLoadingItems(true)
    try {
      const rows = await fetchAdminItems({
        moderation_status: effectiveFilters.moderationFilter === 'all' ? undefined : effectiveFilters.moderationFilter,
        lifecycle: effectiveFilters.lifecycleFilter === 'all' ? undefined : effectiveFilters.lifecycleFilter,
        status: effectiveFilters.statusFilter === 'all' ? undefined : effectiveFilters.statusFilter,
        is_verified: effectiveFilters.verifiedFilter === 'all' ? undefined : effectiveFilters.verifiedFilter === 'verified',
        category: effectiveFilters.categoryFilter || undefined,
        actor_telegram_user_id: effectiveFilters.actorFilter ? Number(effectiveFilters.actorFilter) : undefined,
        q: effectiveFilters.query || undefined,
        created_from: effectiveFilters.createdFrom || undefined,
        created_to: effectiveFilters.createdTo || undefined,
        sort_by: effectiveFilters.sortBy,
        sort_order: effectiveFilters.sortOrder,
        limit: effectiveFilters.limit,
        offset: effectiveOffset,
        suspicious_only: effectiveFilters.suspiciousOnly || undefined,
      })
      setItems(rows)
      const ids = rows.map((item) => item.id)
      const signalRows = ids.length ? await fetchModerationSignals(ids) : []
      setSignals((prev) => ({ ...prev, ...Object.fromEntries(signalRows.map((row) => [row.item_id, row])) }))
      setItemError(null)
    } catch {
      setItemError('Could not load moderation queue.')
    } finally {
      setLoadingItems(false)
    }
  }, [itemFilters, itemsOffset])

  const loadAudit = useCallback(async (nextOffset = auditOffset, nextFilters?: AuditFilters) => {
    const effectiveFilters = nextFilters ?? auditFilters
    setLoadingAudit(true)
    try {
      const rows = await fetchAuditEvents({
        limit: effectiveFilters.auditLimit,
        offset: nextOffset,
        event_type: effectiveFilters.auditType || undefined,
        actor_telegram_user_id: effectiveFilters.auditActor ? Number(effectiveFilters.auditActor) : undefined,
        item_id: effectiveFilters.auditItem ? Number(effectiveFilters.auditItem) : undefined,
        claim_id: effectiveFilters.auditClaim ? Number(effectiveFilters.auditClaim) : undefined,
        created_from: effectiveFilters.auditCreatedFrom || undefined,
        created_to: effectiveFilters.auditCreatedTo || undefined,
      })
      setAuditEvents(rows)
      setAuditError(null)
    } catch {
      setAuditError('Could not load audit events.')
    } finally {
      setLoadingAudit(false)
    }
  }, [auditFilters, auditOffset])

  const loadStats = useCallback(async () => {
    const [nextStats, nextQueueSummary, nextObservability] = await Promise.all([
      fetchModerationStats(),
      fetchAdminQueueSummary(),
      fetchAdminObservability(),
    ])
    setStats(nextStats)
    setQueueSummary(nextQueueSummary)
    setObservability(nextObservability)
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([loadItems(undefined, 0), loadAudit(0), loadStats()])
    setItemsOffset(0)
    setAuditOffset(0)
  }, [loadAudit, loadItems, loadStats])

  const runSingleItemAction = useCallback(async (itemId: number, action: () => Promise<Item>) => {
    setActionLoading(true)
    try {
      const updated = await action()
      setItems((prev) => prev.map((item) => (item.id === itemId ? updated : item)))
      const refreshWarnings: string[] = []
      try {
        const refreshedSignals = await fetchModerationSignals([itemId])
        if (refreshedSignals[0]) {
          setSignals((prev) => ({ ...prev, [itemId]: refreshedSignals[0] }))
        }
      } catch {
        refreshWarnings.push('signal refresh failed')
      }
      try {
        await Promise.all([loadStats(), loadAudit(0)])
        setAuditOffset(0)
      } catch {
        refreshWarnings.push('dashboard refresh failed')
      }
      const suffix = refreshWarnings.length ? ` (${refreshWarnings.join('; ')})` : ''
      setActionMessage(`Action completed for #${itemId}.${suffix}`)
    } catch {
      setActionMessage(`Admin action failed for #${itemId}.`)
    } finally {
      setActionLoading(false)
    }
  }, [loadAudit, loadStats])

  const runBulkAction = useCallback(async (actionLabel: string, action: () => Promise<BulkActionResponse>) => {
    setActionLoading(true)
    try {
      const result = await action()
      const refreshFailures: string[] = []
      await Promise.allSettled([
        loadItems(),
        loadStats(),
        loadAudit(0),
      ]).then((results) => {
        if (results[0].status === 'rejected') refreshFailures.push('queue refresh failed')
        if (results[1].status === 'rejected') refreshFailures.push('stats refresh failed')
        if (results[2].status === 'rejected') refreshFailures.push('audit refresh failed')
      })
      setAuditOffset(0)
      const failedIds = result.results.filter((row) => !row.success).map((row) => row.item_id)
      const failedSegment = failedIds.length ? ` Failed: ${failedIds.slice(0, 8).join(', ')}` : ''
      const refreshSegment = refreshFailures.length ? ` Refresh warnings: ${refreshFailures.join(', ')}.` : ''
      setActionMessage(`${actionLabel}: ${result.succeeded}/${result.processed} succeeded.${failedSegment}${refreshSegment}`)
    } catch {
      setActionMessage(`${actionLabel} failed.`)
    } finally {
      setActionLoading(false)
    }
  }, [loadAudit, loadItems, loadStats])

  const applyPreset = useCallback(async (preset: QueuePreset) => {
    const nextFilters: ItemFilters = {
      ...defaultItemFilters,
      lifecycleFilter: 'active',
    }

    if (preset === 'flagged') {
      nextFilters.moderationFilter = 'flagged'
      nextFilters.sortBy = 'moderated_at'
    } else if (preset === 'pending') {
      nextFilters.moderationFilter = 'pending'
      nextFilters.sortBy = 'created_at'
    } else if (preset === 'recent') {
      nextFilters.moderationFilter = 'all'
      nextFilters.sortBy = 'updated_at'
    } else {
      nextFilters.moderationFilter = 'flagged'
      nextFilters.sortBy = 'moderated_at'
      nextFilters.suspiciousOnly = true
    }

    setItemsOffset(0)
    setItemFilters(nextFilters)
    await loadItems(nextFilters, 0)
  }, [loadItems])

  const summary = useMemo(() => ({
    pending: items.filter((item) => item.moderation_status === 'pending').length,
    flagged: items.filter((item) => item.moderation_status === 'flagged').length,
    approved: items.filter((item) => item.moderation_status === 'approved').length,
    rejected: items.filter((item) => item.moderation_status === 'rejected').length,
  }), [items])

  const flaggedQueue = useMemo(() => items
    .filter((item) => item.moderation_status === 'flagged')
    .sort((a, b) => ((signals[b.id]?.recent_flags_24h ?? 0) + (signals[b.id]?.blocked_events_24h ?? 0)) - ((signals[a.id]?.recent_flags_24h ?? 0) + (signals[a.id]?.blocked_events_24h ?? 0))), [items, signals])

  const pendingQueue = useMemo(() => items.filter((item) => item.moderation_status === 'pending'), [items])

  return {
    items,
    signals,
    stats,
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
    actionLoading,
    itemError,
    auditError,
    actionMessage,
    setActionMessage,
    loadItems,
    loadAudit,
    loadStats,
    refreshAll,
    runSingleItemAction,
    runBulkAction,
    applyPreset,
    summary,
    flaggedQueue,
    pendingQueue,
  }
}

export const itemModerationAction = (
  itemId: number,
  action: 'approve' | 'reject' | 'flag' | 'unflag',
  reason?: string,
) => moderateItem(itemId, action, reason)

export const itemVerifyAction = (itemId: number, isVerified: boolean) => verifyItemAdmin(itemId, isVerified)

export const itemLifecycleAction = (itemId: number, action: 'resolve' | 'reopen' | 'delete') => lifecycleItemAdmin(itemId, action)

export const bulkModerationAction = (itemIds: number[], action: 'approve' | 'reject' | 'flag' | 'unflag', reason?: string) => bulkModerateItems(itemIds, action, reason)

export const bulkVerifyAction = (itemIds: number[], isVerified: boolean) => bulkVerifyItems(itemIds, isVerified)

export const bulkLifecycleAction = (itemIds: number[], action: 'resolve' | 'reopen' | 'delete') => bulkLifecycleItems(itemIds, action)
