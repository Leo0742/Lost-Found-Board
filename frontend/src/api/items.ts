import { apiClient } from './client'
import { Item, NewItemPayload, ItemStatus, MatchResult, ItemLifecycle } from '../types/item'

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

export const resolveItem = async (itemId: number, telegramUserId: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/resolve`, { telegram_user_id: telegramUserId })
  return response.data
}

export const reopenItem = async (itemId: number, telegramUserId: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/reopen`, { telegram_user_id: telegramUserId })
  return response.data
}

export const softDeleteItem = async (itemId: number, telegramUserId: number) => {
  const response = await apiClient.post<Item>(`/items/${itemId}/delete`, { telegram_user_id: telegramUserId })
  return response.data
}
