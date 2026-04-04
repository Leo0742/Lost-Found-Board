import { apiClient } from './client'
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
  actor_telegram_user_id?: number | null
  item_id?: number | null
  claim_id?: number | null
  details?: Record<string, unknown>
  created_at: string
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

export const getAuthMe = async () => {
  return cachedCall('auth:me', 15_000, async () => {
    const response = await apiClient.get<WhoAmI>('/auth/me')
    return response.data
  })
}

export const generateLinkCode = async () => {
  const response = await apiClient.post<{ code: string; expires_at: string }>('/auth/link-code')
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

const ownerPayload = (telegramUserId?: number) => (telegramUserId ? { telegram_user_id: telegramUserId } : {})

export const resolveItem = async (itemId: number, telegramUserId?: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/resolve`, ownerPayload(telegramUserId))
  return response.data
}

export const reopenItem = async (itemId: number, telegramUserId?: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/reopen`, ownerPayload(telegramUserId))
  return response.data
}

export const softDeleteItem = async (itemId: number, telegramUserId?: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/delete`, ownerPayload(telegramUserId))
  return response.data
}

export const flagItem = async (itemId: number, reason: string) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/flag`, { reason })
  return response.data
}

export const fetchMyItems = async () => {
  const response = await apiClient.get<Item[]>('/items/me')
  return response.data
}

export const fetchAdminItems = async (params: { moderation_status?: string; lifecycle?: string; q?: string }) => {
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

export const fetchAuditEvents = async (params: { event_type?: string; actor_telegram_user_id?: number; item_id?: number; claim_id?: number; limit?: number }) => {
  const response = await apiClient.get<AuditEvent[]>('/items/admin/audit-events', { params })
  return response.data
}

export const createClaim = async (source_item_id: number, target_item_id: number, requester_telegram_user_id?: number, claim_message?: string) => {
  const response = await apiClient.post('/items/claim-requests', { source_item_id, target_item_id, requester_telegram_user_id, claim_message })
  invalidateCache('claims:')
  return response.data
}

export const listClaims = async (telegram_user_id?: number, direction: 'all' | 'incoming' | 'outgoing' = 'all') => {
  const key = `claims:${direction}:${telegram_user_id ?? 'session'}`
  return cachedCall(key, 7_500, async () => {
    const response = await apiClient.get('/items/claim-requests', { params: { telegram_user_id, direction } })
    return response.data
  })
}

export const claimAction = async (claimId: number, action: 'approve' | 'reject' | 'cancel' | 'complete' | 'not-match', telegram_user_id?: number, note?: string) => {
  const response = await apiClient.post(`/items/claim-requests/${claimId}/${action}`, { telegram_user_id, note })
  invalidateCache('claims:')
  return response.data
}
