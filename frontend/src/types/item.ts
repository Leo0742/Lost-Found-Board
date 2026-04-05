export type ItemStatus = 'lost' | 'found'
export type ItemLifecycle = 'active' | 'resolved' | 'deleted'
export type ModerationStatus = 'pending' | 'approved' | 'rejected' | 'flagged'

export interface Item {
  id: number
  title: string
  description: string
  category: string
  location: string
  status: ItemStatus
  lifecycle: ItemLifecycle
  moderation_status: ModerationStatus
  moderation_reason?: string | null
  moderated_at?: string | null
  moderated_by?: string | null
  is_verified: boolean
  verified_at?: string | null
  contact_name?: string | null
  telegram_username?: string | null
  telegram_user_id?: number | null
  owner_telegram_user_id?: number | null
  owner_telegram_username?: string | null
  owner_display_name?: string | null
  image_path?: string | null
  image_filename?: string | null
  image_mime_type?: string | null
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
  owner_telegram_user_id?: number
  owner_telegram_username?: string
  owner_display_name?: string
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
  image_path?: string | null
}

export interface Claim {
  id: number
  source_item_id: number
  target_item_id: number
  requester_telegram_user_id?: number | null
  owner_telegram_user_id?: number | null
  status: 'pending' | 'approved' | 'rejected' | 'cancelled' | 'completed' | 'not_match'
  claim_message?: string | null
  source_item_title?: string | null
  target_item_title?: string | null
  shared_source_contact?: string | null
  shared_target_contact?: string | null
  shared_source_address?: string | null
  shared_target_address?: string | null
}
