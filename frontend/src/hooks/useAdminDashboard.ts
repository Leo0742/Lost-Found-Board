import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

export type QueuePreset = 'flagged' | 'suspicious'

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
  limit: 50,
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

const PRESET_FILTERS: Record<QueuePreset, ItemFilters> = {
  flagged: {
    ...defaultItemFilters,
    lifecycleFilter: 'active',
    moderationFilter: 'flagged',
    sortBy: 'moderated_at',
  },
  suspicious: {
    ...defaultItemFilters,
    lifecycleFilter: 'active',
    moderationFilter: 'flagged',
    sortBy: 'moderated_at',
    suspiciousOnly: true,
  },
}

export const useAdminDashboard = () => {
  const [items, setItems] = useState<Item[]>([])
  const [signals, setSignals] = useState<Record<number, ModerationSignal>>({})
  const [stats, setStats] = useState<ModerationStats | null>(null)
  const [queueSummary, setQueueSummary] = useState<AdminQueueSummary | null>(null)
  const [observability, setObservability] = useState<AdminObservability | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [itemFilters, setItemFiltersState] = useState<ItemFilters>(defaultItemFilters)
  const [activePreset, setActivePreset] = useState<QueuePreset | null>(null)
  const [auditFilters, setAuditFilters] = useState<AuditFilters>(defaultAuditFilters)
  const [itemsOffset, setItemsOffset] = useState(0)
  const [auditOffset, setAuditOffset] = useState(0)
  const [loadingItems, setLoadingItems] = useState(false)
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [loadingStats, setLoadingStats] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [itemError, setItemError] = useState<string | null>(null)
  const [signalError, setSignalError] = useState<string | null>(null)
  const [auditError, setAuditError] = useState<string | null>(null)
  const [statsError, setStatsError] = useState<string | null>(null)
  const [queueSummaryError, setQueueSummaryError] = useState<string | null>(null)
  const [observabilityError, setObservabilityError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionWarning, setActionWarning] = useState<string | null>(null)
  const signalsRef = useRef<Record<number, ModerationSignal>>({})
  const itemsRequestVersionRef = useRef(0)
  const auditRequestVersionRef = useRef(0)
  const statsRequestVersionRef = useRef(0)

  useEffect(() => {
    signalsRef.current = signals
  }, [signals])

  const loadItems = useCallback(async (nextFilters?: ItemFilters, nextOffset?: number, options?: { forceSignals?: boolean }) => {
    const requestVersion = ++itemsRequestVersionRef.current
    const effectiveFilters = nextFilters ?? itemFilters
    const effectiveOffset = nextOffset ?? itemsOffset
    setLoadingItems(true)
    setItemError(null)
    try {
      const actorFilterRaw = effectiveFilters.actorFilter.trim()
      const actorFilterId = actorFilterRaw ? Number(actorFilterRaw) : undefined
      const rows = await fetchAdminItems({
        moderation_status: effectiveFilters.moderationFilter === 'all' ? undefined : effectiveFilters.moderationFilter,
        lifecycle: effectiveFilters.lifecycleFilter === 'all' ? undefined : effectiveFilters.lifecycleFilter,
        status: effectiveFilters.statusFilter === 'all' ? undefined : effectiveFilters.statusFilter,
        is_verified: effectiveFilters.verifiedFilter === 'all' ? undefined : effectiveFilters.verifiedFilter === 'verified',
        category: effectiveFilters.categoryFilter || undefined,
        actor_telegram_user_id: Number.isFinite(actorFilterId) ? actorFilterId : undefined,
        q: effectiveFilters.query || undefined,
        created_from: effectiveFilters.createdFrom || undefined,
        created_to: effectiveFilters.createdTo || undefined,
        sort_by: effectiveFilters.sortBy,
        sort_order: effectiveFilters.sortOrder,
        limit: effectiveFilters.limit,
        offset: effectiveOffset,
        suspicious_only: effectiveFilters.suspiciousOnly || undefined,
      })
      if (requestVersion !== itemsRequestVersionRef.current) return
      setItems(rows)
      setItemError(null)
      const ids = rows.map((item) => item.id)
      const signalIds = options?.forceSignals ? ids : ids.filter((id) => !signalsRef.current[id])
      if (signalIds.length) {
        try {
          const signalRows = await fetchModerationSignals(signalIds)
          if (requestVersion !== itemsRequestVersionRef.current) return
          setSignals((prev) => ({ ...prev, ...Object.fromEntries(signalRows.map((row) => [row.item_id, row])) }))
          setSignalError(null)
        } catch {
          if (requestVersion !== itemsRequestVersionRef.current) return
          setSignalError('Moderation signals are temporarily unavailable. Queue rows are still current.')
        }
      } else {
        setSignalError(null)
      }
    } catch {
      if (requestVersion !== itemsRequestVersionRef.current) return
      setItemError('Could not load moderation queue.')
    } finally {
      if (requestVersion === itemsRequestVersionRef.current) {
        setLoadingItems(false)
      }
    }
  }, [itemFilters, itemsOffset])

  const loadAudit = useCallback(async (nextOffset = auditOffset, nextFilters?: AuditFilters) => {
    const requestVersion = ++auditRequestVersionRef.current
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
      if (requestVersion !== auditRequestVersionRef.current) return
      setAuditEvents(rows)
      setAuditError(null)
    } catch {
      if (requestVersion !== auditRequestVersionRef.current) return
      setAuditError('Could not load audit events.')
    } finally {
      if (requestVersion === auditRequestVersionRef.current) {
        setLoadingAudit(false)
      }
    }
  }, [auditFilters, auditOffset])

  const loadStats = useCallback(async () => {
    const requestVersion = ++statsRequestVersionRef.current
    setLoadingStats(true)
    const [statsResult, queueResult, observabilityResult] = await Promise.allSettled([
      fetchModerationStats(),
      fetchAdminQueueSummary(),
      fetchAdminObservability(),
    ])
    if (requestVersion !== statsRequestVersionRef.current) return
    if (statsResult.status === 'fulfilled') {
      setStats(statsResult.value)
      setStatsError(null)
    } else {
      setStatsError('Could not load moderation stats.')
    }
    if (queueResult.status === 'fulfilled') {
      setQueueSummary(queueResult.value)
      setQueueSummaryError(null)
    } else {
      setQueueSummaryError('Could not load queue summary.')
    }
    if (observabilityResult.status === 'fulfilled') {
      setObservability(observabilityResult.value)
      setObservabilityError(null)
    } else {
      setObservabilityError('Could not load observability metrics.')
    }
    setLoadingStats(false)
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.allSettled([loadItems(undefined, 0, { forceSignals: true }), loadAudit(0), loadStats()])
    setItemsOffset(0)
    setAuditOffset(0)
  }, [loadAudit, loadItems, loadStats])

  const collectRefreshWarnings = useCallback(async (refreshers: Record<string, () => Promise<unknown>>) => {
    const entries = Object.entries(refreshers)
    const settled = await Promise.allSettled(entries.map(([, fn]) => fn()))
    return settled
      .map((result, idx) => (result.status === 'rejected' ? entries[idx][0] : null))
      .filter((label): label is string => Boolean(label))
  }, [])

  const runSingleItemAction = useCallback(async (itemId: number, action: () => Promise<Item>) => {
    setActionLoading(true)
    setActionWarning(null)
    try {
      const updated = await action()
      setItems((prev) => prev.map((item) => (item.id === itemId ? updated : item)))
      const refreshWarnings = await collectRefreshWarnings({
        'signal refresh failed': async () => {
          const refreshedSignals = await fetchModerationSignals([itemId])
          if (refreshedSignals[0]) {
            setSignals((prev) => ({ ...prev, [itemId]: refreshedSignals[0] }))
          }
        },
        'stats refresh failed': loadStats,
        'audit refresh failed': async () => {
          await loadAudit(0)
          setAuditOffset(0)
        },
      })
      setActionMessage(`Action completed for #${itemId}.`)
      if (refreshWarnings.length) {
        setActionWarning(`Action succeeded for #${itemId}, but ${refreshWarnings.join(', ')}.`)
      }
    } catch {
      setActionMessage(`Admin action failed for #${itemId}.`)
    } finally {
      setActionLoading(false)
    }
  }, [collectRefreshWarnings, loadAudit, loadStats])

  const runBulkAction = useCallback(async (actionLabel: string, action: () => Promise<BulkActionResponse>) => {
    setActionLoading(true)
    setActionWarning(null)
    try {
      const result = await action()
      const refreshFailures = await collectRefreshWarnings({
        'queue refresh failed': () => loadItems(),
        'stats refresh failed': loadStats,
        'audit refresh failed': async () => {
          await loadAudit(0)
          setAuditOffset(0)
        },
      })
      setAuditOffset(0)
      const failedIds = result.results.filter((row) => !row.success).map((row) => row.item_id)
      const failedSegment = failedIds.length ? ` Failed: ${failedIds.slice(0, 8).join(', ')}` : ''
      setActionMessage(`${actionLabel}: ${result.succeeded}/${result.processed} succeeded.${failedSegment}`)
      if (refreshFailures.length) {
        setActionWarning(`${actionLabel} succeeded, but ${refreshFailures.join(', ')}.`)
      }
    } catch {
      setActionMessage(`${actionLabel} failed.`)
    } finally {
      setActionLoading(false)
    }
  }, [collectRefreshWarnings, loadAudit, loadItems, loadStats])

  const applyPreset = useCallback(async (preset: QueuePreset) => {
    const nextFilters = { ...PRESET_FILTERS[preset] }
    setActivePreset(preset)
    setItemsOffset(0)
    setItemFiltersState(nextFilters)
    await loadItems(nextFilters, 0, { forceSignals: true })
  }, [loadItems])

  const setItemFilters = useCallback((nextFilters: ItemFilters) => {
    setActivePreset(null)
    setItemFiltersState(nextFilters)
  }, [])

  const summary = useMemo(() => ({
    pending: items.filter((item) => item.moderation_status === 'pending').length,
    flagged: items.filter((item) => item.moderation_status === 'flagged').length,
    approved: items.filter((item) => item.moderation_status === 'approved').length,
    rejected: items.filter((item) => item.moderation_status === 'rejected').length,
  }), [items])

  const flaggedQueue = useMemo(() => items
    .filter((item) => item.moderation_status === 'flagged')
    .sort((a, b) => ((signals[b.id]?.recent_flags_24h ?? 0) + (signals[b.id]?.blocked_events_24h ?? 0)) - ((signals[a.id]?.recent_flags_24h ?? 0) + (signals[a.id]?.blocked_events_24h ?? 0))), [items, signals])

  return {
    items,
    signals,
    stats,
    queueSummary,
    observability,
    auditEvents,
    itemFilters,
    setItemFilters,
    activePreset,
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
    loadStats,
    refreshAll,
    runSingleItemAction,
    runBulkAction,
    applyPreset,
    summary,
    flaggedQueue,
  }
}

export const itemModerationAction = (
  itemId: number,
  action: 'flag' | 'unflag',
  reason?: string,
) => moderateItem(itemId, action, reason)

export const itemVerifyAction = (itemId: number, isVerified: boolean) => verifyItemAdmin(itemId, isVerified)

export const itemLifecycleAction = (itemId: number, action: 'resolve' | 'reopen' | 'delete') => lifecycleItemAdmin(itemId, action)

export const bulkModerationAction = (itemIds: number[], action: 'flag' | 'unflag', reason?: string) => bulkModerateItems(itemIds, action, reason)

export const bulkVerifyAction = (itemIds: number[], isVerified: boolean) => bulkVerifyItems(itemIds, isVerified)

export const bulkLifecycleAction = (itemIds: number[], action: 'resolve' | 'reopen' | 'delete') => bulkLifecycleItems(itemIds, action)
