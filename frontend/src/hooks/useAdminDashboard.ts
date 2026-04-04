import { useCallback, useMemo, useState } from 'react'
import {
  fetchAdminItems,
  fetchAuditEvents,
  fetchModerationSignals,
  fetchModerationStats,
  moderateItem,
  verifyItemAdmin,
  lifecycleItemAdmin,
  type AuditEvent,
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
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [itemFilters, setItemFilters] = useState<ItemFilters>(defaultItemFilters)
  const [auditFilters, setAuditFilters] = useState<AuditFilters>(defaultAuditFilters)
  const [auditOffset, setAuditOffset] = useState(0)
  const [loadingItems, setLoadingItems] = useState(false)
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadItems = useCallback(async (nextFilters?: ItemFilters) => {
    const effectiveFilters = nextFilters ?? itemFilters
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
        limit: 200,
      })
      setItems(rows)
      const signalRows = rows.length ? await fetchModerationSignals(rows.map((item) => item.id)) : []
      setSignals(Object.fromEntries(signalRows.map((row) => [row.item_id, row])))
      setError(null)
    } catch {
      setError('Could not load moderation queue.')
    } finally {
      setLoadingItems(false)
    }
  }, [itemFilters])

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
      setError(null)
    } catch {
      setError('Could not load audit events.')
    } finally {
      setLoadingAudit(false)
    }
  }, [auditFilters, auditOffset])

  const loadStats = useCallback(async () => {
    try {
      setStats(await fetchModerationStats())
    } catch {
      setError('Could not load moderation stats.')
    }
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([loadItems(), loadAudit(0), loadStats()])
    setAuditOffset(0)
  }, [loadAudit, loadItems, loadStats])

  const runModerationAction = useCallback(async (action: () => Promise<unknown>) => {
    try {
      await action()
      await refreshAll()
    } catch {
      setError('Admin action failed.')
    }
  }, [refreshAll])

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
      nextFilters.query = 'duplicate'
    }

    setItemFilters(nextFilters)
    await loadItems(nextFilters)
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
    refreshAll,
    runModerationAction,
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
