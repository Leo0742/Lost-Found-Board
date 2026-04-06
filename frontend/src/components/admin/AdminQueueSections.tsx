import { Item } from '../../types/item'
import { ModerationSignal } from '../../api/items'
import { ModerationSignals } from './ModerationSignals'

type QueueProps = {
  items: Item[]
  signals: Record<number, ModerationSignal>
  selectedIds?: number[]
  onToggleSelected?: (itemId: number) => void
  onApprove: (itemId: number) => void
  onReject: (itemId: number) => void
  onFlag: (itemId: number) => void
  onUnflag: (itemId: number) => void
}

export const ModerationQueueFeed = ({
  items,
  signals,
  selectedIds = [],
  onToggleSelected,
  onApprove,
  onReject,
  onFlag,
  onUnflag,
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
          <button onClick={() => onApprove(item.id)}>Approve</button>
          <button className="button-neutral" onClick={() => onReject(item.id)}>Reject</button>
          {item.moderation_status === 'flagged' ? (
            <button className="button-ghost" onClick={() => onUnflag(item.id)}>Unflag</button>
          ) : (
            <button className="button-ghost" onClick={() => onFlag(item.id)}>Flag</button>
          )}
        </div>
      </article>
    ))}
  </>
)
