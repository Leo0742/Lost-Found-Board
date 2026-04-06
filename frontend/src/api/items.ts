import { apiClient, refreshCsrfToken } from './client'
import { Item, NewItemPayload, ItemStatus, MatchResult, ItemLifecycle } from '../types/item'
import { cachedCall, invalidateCache } from './cache'

export type TelegramIdentity = {
  telegram_user_id: number
  telegram_username?: string | null
  display_name?: string | null
}

export type WhoAmI = {
  linked: boolean
  identity?: TelegramIdentity | null
  admin_access: boolean
  role?: 'admin' | 'moderator' | null
}

export type AuditEvent = {
  id: number
  event_type: string
  label?: string | null
  summary?: string | null
  actor_telegram_user_id?: number | null
  item_id?: number | null
  claim_id?: number | null
  details?: Record<string, unknown>
  item_url?: string | null
  claim_url?: string | null
  created_at: string
}

export type ModerationSignal = {
  item_id: number
  total_flags: number
  recent_flags_24h: number
  recent_claims_24h: number
  claim_count: number
  duplicate_flags_24h: number
  blocked_events_24h: number
  last_flag_at?: string | null
  suspicion_markers: string[]
}



export type ProfileContactMethod = {
  id: string
  name: string
  value: string
}

export type ProfileAddress = {
  id: string
  label: string
  address_text: string
  latitude?: number | null
  longitude?: number | null
  extra_details?: string | null
}

export type UserProfile = {
  telegram_user_id: number
  telegram_username?: string | null
  telegram_display_name?: string | null
  display_name?: string | null
  preferred_contact_method?: string | null
  preferred_contact_details?: string | null
  pickup_location?: string | null
  avatar_url?: string | null
  telegram_avatar_url?: string | null
  contact_methods?: ProfileContactMethod[]
  exposed_contact_methods?: ProfileContactMethod[]
  contact_visibility?: "all" | "one"
  contact_visibility_method_id?: string | null
  profile_addresses?: ProfileAddress[]
  exposed_profile_addresses?: ProfileAddress[]
  address_visibility?: "all" | "one"
  address_visibility_address_id?: string | null
  updated_at?: string | null
}

export type UserProfileUpdate = {
  display_name?: string | null
  preferred_contact_method?: string | null
  preferred_contact_details?: string | null
  pickup_location?: string | null
  avatar_url?: string | null
  contact_methods?: ProfileContactMethod[] | null
  contact_visibility?: "all" | "one"
  contact_visibility_method_id?: string | null
  profile_addresses?: ProfileAddress[] | null
  address_visibility?: "all" | "one"
  address_visibility_address_id?: string | null
}

export type AdminItemsParams = {
  moderation_status?: string
  lifecycle?: string
  q?: string
  category?: string
  status?: string
  is_verified?: boolean
  actor_telegram_user_id?: number
  created_from?: string
  created_to?: string
  sort_by?: string
  sort_order?: string
  limit?: number
  offset?: number
  suspicious_only?: boolean
}

export type AuditEventsParams = {
  event_type?: string
  actor_telegram_user_id?: number
  item_id?: number
  claim_id?: number
  limit?: number
  offset?: number
  created_from?: string
  created_to?: string
}
export type ModerationStats = {
  pending: number
  flagged: number
  active: number
  unresolved_claims: number
  recent_abuse_blocks_24h: number
}

export type BulkActionResult = {
  item_id: number
  success: boolean
  detail?: string | null
}

export type BulkActionResponse = {
  action: string
  processed: number
  succeeded: number
  failed: number
  results: BulkActionResult[]
}

export type AdminQueueSummary = {
  pending_total: number
  flagged_total: number
  approved_total: number
  rejected_total: number
  high_risk_flagged_24h: number
  stale_pending_48h: number
}

export type AdminObservability = {
  recent_abuse_blocks_24h: number
  duplicate_flags_24h: number
  duplicate_claims_24h: number
  blocked_admin_audit_queries_24h: number
  claims_created_24h: number
  unresolved_claims_total: number
  cleanup: {
    anti_abuse_retention_days: number
    audit_retention_days: number
    media_temp_interval_minutes: number
    media_orphan_interval_minutes: number
    event_retention_interval_minutes: number
    maintenance_status?: Record<string, {
      last_attempt_at?: string | null
      last_success_at?: string | null
      last_error_at?: string | null
      last_error?: string | null
      health?: 'healthy' | 'warning' | 'stale' | 'unknown'
      stale_seconds?: number | null
      last_removed_count?: number
      total_removed?: number
      runs?: number
      failures?: number
    }>
  }
  semantic_runtime: Record<string, unknown>
}

export const fetchItems = async (params: { q?: string; status?: ItemStatus | 'all'; category?: string; lifecycle?: ItemLifecycle | 'all' }) => {
  const query: Record<string, string> = {}
  if (params.q) query.q = params.q
  if (params.category) query.category = params.category
  if (params.status && params.status !== 'all') query.status = params.status
  if (params.lifecycle && params.lifecycle !== 'all') query.lifecycle = params.lifecycle

  const response = await apiClient.get<Item[]>('/items', { params: query })
  return response.data
}

export const fetchItem = async (id: string) => {
  const response = await apiClient.get<Item>(`/items/${id}`)
  return response.data
}

export const fetchMatches = async (id: string) => {
  const response = await apiClient.get<MatchResult[]>(`/items/matches/${id}`)
  return response.data
}

export const createItem = async (payload: NewItemPayload) => {
  const response = await apiClient.post<Item>('/items', payload)
  return response.data
}

export const createWebSession = async () => {
  const response = await apiClient.post<{ session_id: string; expires_at: string }>('/auth/session')
  return response.data
}

export const getAuthMe = async (options?: { forceRefresh?: boolean }) => {
  if (options?.forceRefresh) {
    invalidateCache('auth:me')
  }
  return cachedCall('auth:me', 15_000, async () => {
    const response = await apiClient.get<WhoAmI>('/auth/me')
    return response.data
  })
}

export const generateLinkCode = async () => {
  const response = await apiClient.post<{ code: string; expires_at: string }>('/auth/link-code')
  return response.data
}


export const fetchMyProfile = async (options?: { bypassCache?: boolean }) => {
  const response = await apiClient.get<UserProfile>('/profile/me', options?.bypassCache
    ? {
        params: { ts: Date.now() },
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          Pragma: 'no-cache',
        },
      }
    : undefined)
  return response.data
}

export const updateMyProfile = async (payload: UserProfileUpdate) => {
  const response = await apiClient.put<UserProfile>('/profile/me', payload)
  return response.data
}

export const fetchCategories = async () => {
  return cachedCall('items:categories', 60_000, async () => {
    const response = await apiClient.get<string[]>('/items/categories')
    return response.data
  })
}

export const suggestCategory = async (title: string) => {
  const response = await apiClient.get<{ category: string; confidence: number; reasons: string[] }>('/items/category-suggest', {
    params: { title }
  })
  return response.data
}

export const unlinkTelegram = async () => {
  await apiClient.post('/auth/unlink')
  await refreshCsrfToken()
  invalidateCache('auth:')
}

export const uploadItemImage = async (file: File) => {
  const form = new FormData()
  form.append('image', file)
  const response = await apiClient.post<{ image_path: string; image_filename: string; image_mime_type: string; image_url: string }>(
    '/items/upload-image',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return response.data
}

export const resolveItem = async (itemId: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/resolve`, {})
  return response.data
}

export const reopenItem = async (itemId: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/reopen`, {})
  return response.data
}

export const deleteItemPermanently = async (itemId: number) => {
  await apiClient.delete(`/items/${itemId}/owner-delete`)
}

export const flagItem = async (itemId: number, reason: string) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/flag`, { reason })
  return response.data
}

export const fetchMyItems = async () => {
  const response = await apiClient.get<Item[]>('/items/me')
  return response.data
}

export const fetchAdminItems = async (params: AdminItemsParams) => {
  const response = await apiClient.get<Item[]>('/items/admin/items', {
    params
  })
  return response.data
}

export const moderateItem = async (itemId: number, action: 'approve' | 'reject' | 'flag' | 'unflag', reason?: string) => {
  const response = await apiClient.post<Item>(`/items/admin/items/${itemId}/moderate`, { action, reason })
  return response.data
}

export const verifyItemAdmin = async (itemId: number, is_verified: boolean) => {
  const response = await apiClient.post<Item>(`/items/admin/items/${itemId}/verify`, { is_verified })
  return response.data
}

export const lifecycleItemAdmin = async (itemId: number, action: 'resolve' | 'reopen' | 'delete') => {
  const response = await apiClient.post<Item>(`/items/admin/items/${itemId}/lifecycle`, { action })
  return response.data
}

export const fetchAuditEvents = async (params: AuditEventsParams) => {
  const response = await apiClient.get<AuditEvent[]>('/items/admin/audit-events', { params })
  return response.data
}

export const fetchModerationSignals = async (itemIds: number[]) => {
  const response = await apiClient.get<ModerationSignal[]>('/items/admin/moderation-signals', { params: { item_ids: itemIds } })
  return response.data
}

export const fetchModerationStats = async () => {
  const response = await apiClient.get<ModerationStats>('/items/admin/moderation-stats')
  return response.data
}

export const bulkModerateItems = async (item_ids: number[], action: 'approve' | 'reject' | 'flag' | 'unflag', reason?: string) => {
  const response = await apiClient.post<BulkActionResponse>('/items/admin/items/bulk-moderate', { item_ids, action, reason })
  return response.data
}

export const bulkVerifyItems = async (item_ids: number[], is_verified: boolean) => {
  const response = await apiClient.post<BulkActionResponse>('/items/admin/items/bulk-verify', { item_ids, is_verified })
  return response.data
}

export const bulkLifecycleItems = async (item_ids: number[], action: 'resolve' | 'reopen' | 'delete') => {
  const response = await apiClient.post<BulkActionResponse>('/items/admin/items/bulk-lifecycle', { item_ids, action })
  return response.data
}

export const fetchAdminQueueSummary = async () => {
  const response = await apiClient.get<AdminQueueSummary>('/items/admin/queue-summary')
  return response.data
}

export const fetchAdminObservability = async () => {
  const response = await apiClient.get<AdminObservability>('/items/admin/observability')
  return response.data
}

export const createClaim = async (source_item_id: number, target_item_id: number, claim_message?: string) => {
  const response = await apiClient.post('/items/claim-requests', { source_item_id, target_item_id, claim_message })
  invalidateCache('claims:')
  return response.data
}

export const listClaims = async (direction: 'all' | 'incoming' | 'outgoing' = 'all') => {
  const key = `claims:${direction}:session`
  return cachedCall(key, 7_500, async () => {
    const response = await apiClient.get('/items/claim-requests', { params: { direction } })
    return response.data
  })
}

export const claimAction = async (claimId: number, action: 'approve' | 'reject' | 'cancel' | 'complete' | 'not-match', note?: string) => {
  const response = await apiClient.post(`/items/claim-requests/${claimId}/${action}`, { note })
  invalidateCache('claims:')
  return response.data
}

export const shareClaimLiveLocation = async (claimId: number, payload: { latitude: number; longitude: number; address_text?: string; ttl_minutes?: number }) => {
  const response = await apiClient.post(`/items/claim-requests/${claimId}/share-live-location`, payload)
  invalidateCache('claims:')
  return response.data
}
