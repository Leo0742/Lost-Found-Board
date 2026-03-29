import { apiClient } from './client'
import { Item, NewItemPayload, ItemStatus, MatchResult } from '../types/item'

export const fetchItems = async (params: { q?: string; status?: ItemStatus | 'all'; category?: string }) => {
  const query: Record<string, string> = {}
  if (params.q) query.q = params.q
  if (params.category) query.category = params.category
  if (params.status && params.status !== 'all') query.status = params.status

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
