import { Item } from '../../types/item'
import { ModerationSignal } from '../../api/items'
import { ModerationSignals } from './ModerationSignals'

type QueueProps = {
  items: Item[]
  signals: Record<number, ModerationSignal>
  selectedIds?: number[]
  onToggleSelected?: (itemId: number) => void
  canDelete: boolean
  onDelete: (itemId: number) => void
  onIgnoreComplaint: (itemId: number) => void
}

export const ModerationQueueFeed = ({
  items,
  signals,
  selectedIds = [],
  onToggleSelected,
  canDelete,
  onDelete,
  onIgnoreComplaint,
}: QueueProps) => (
  <>
    {items.length === 0 ? <p className="subtle">No reports in this queue.</p> : items.map((item) => (
      <article className="card stack" key={item.id}>
        {onToggleSelected ? (
          <label className="queue-select">
            <input type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => onToggleSelected(item.id)} /> Select #{item.id}
          </label>
        ) : null}
        <strong>#{item.id} {item.title}</strong>
        <p className="subtle">{item.category} · {item.location} · @{item.owner_telegram_username || item.telegram_username || 'n/a'}</p>
        <ModerationSignals signal={signals[item.id]} />
        <div className="actions-row">
          <button className="button-neutral" onClick={() => onIgnoreComplaint(item.id)}>Ignore complaint</button>
          {canDelete ? <button className="button-danger" onClick={() => onDelete(item.id)}>Delete post</button> : null}
        </div>
      </article>
    ))}
  </>
)
