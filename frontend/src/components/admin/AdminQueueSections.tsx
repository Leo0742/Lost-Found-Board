import { Item } from '../../types/item'
import { ModerationSignal } from '../../api/items'
import { ModerationSignals } from './ModerationSignals'

type QueueProps = {
  items: Item[]
  signals: Record<number, ModerationSignal>
  onApprove: (itemId: number) => void
  onReject: (itemId: number) => void
  onFlag: (itemId: number) => void
  onUnflag: (itemId: number) => void
}

export const FlaggedQueueSection = ({ items, signals, onApprove, onReject, onUnflag }: Omit<QueueProps, 'onFlag'>) => (
  <>
    {items.length === 0 ? <p className="subtle">No flagged reports.</p> : items.map((item) => (
      <article className="card stack" key={item.id}>
        <strong>#{item.id} {item.title}</strong>
        <p className="subtle">Risk context from flags, duplicate pressure, claims, and blocked abuse events.</p>
        <ModerationSignals signal={signals[item.id]} />
        <div className="actions-row">
          <button onClick={() => onApprove(item.id)}>Approve</button>
          <button className="button-neutral" onClick={() => onReject(item.id)}>Reject</button>
          <button className="button-neutral" onClick={() => onUnflag(item.id)}>Unflag</button>
        </div>
      </article>
    ))}
  </>
)

export const PendingQueueSection = ({ items, onApprove, onFlag }: Pick<QueueProps, 'items' | 'onApprove' | 'onFlag'>) => (
  <>
    {items.length === 0 ? <p className="subtle">No pending reports.</p> : items.map((item) => (
      <article className="card stack" key={item.id}>
        <strong>#{item.id} {item.title}</strong>
        <p className="subtle">{item.category} · {item.location}</p>
        <div className="actions-row">
          <button onClick={() => onApprove(item.id)}>Approve</button>
          <button className="button-ghost" onClick={() => onFlag(item.id)}>Flag</button>
        </div>
      </article>
    ))}
  </>
)
