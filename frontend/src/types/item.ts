export type ItemStatus = 'lost' | 'found'
export type ItemLifecycle = 'active' | 'resolved' | 'deleted'

export interface Item {
  id: number
  title: string
  description: string
  category: string
  location: string
  status: ItemStatus
  lifecycle: ItemLifecycle
  contact_name: string
  telegram_username?: string | null
  telegram_user_id?: number | null
  created_at: string
  updated_at: string
  resolved_at?: string | null
  deleted_at?: string | null
}

export interface NewItemPayload {
  title: string
  description: string
  category: string
  location: string
  status: ItemStatus
  contact_name: string
  telegram_username?: string
  telegram_user_id?: number
}


export interface MatchResult {
  id: number
  title: string
  status: ItemStatus
  category: string
  location: string
  relevance_score: number
  confidence: 'low' | 'medium' | 'high'
  reasons: string[]
  telegram_user_id?: number | null
}
