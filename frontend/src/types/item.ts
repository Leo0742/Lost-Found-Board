export type ItemStatus = 'lost' | 'found'

export interface Item {
  id: number
  title: string
  description: string
  category: string
  location: string
  status: ItemStatus
  contact_name: string
  telegram_username?: string | null
  telegram_user_id?: number | null
  created_at: string
  updated_at: string
}

export interface NewItemPayload {
  title: string
  description: string
  category: string
  location: string
  status: ItemStatus
  contact_name: string
  telegram_username?: string
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
}
