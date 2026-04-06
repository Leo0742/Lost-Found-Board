import { ModerationSignal } from '../../api/items'
import { Item } from '../../types/item'
import { EmptyState } from '../ui'
import { ModerationSignals } from './ModerationSignals'

type Props = {
  items: Item[]
  signals: Record<number, ModerationSignal>
  role: 'admin' | 'moderator' | null
  selectedIds: number[]
  onToggleSelected: (itemId: number) => void
  onSelectAllVisible: () => void
  onClearSelection: () => void
  onBulkIgnoreComplaints: () => void
  onBulkDelete: () => void
  onIgnoreComplaint: (itemId: number) => void
  onDelete: (itemId: number) => void
}

export const AllReportsSection = ({
  items,
  signals,
  role,
  selectedIds,
  onToggleSelected,
  onSelectAllVisible,
  onClearSelection,
  onBulkIgnoreComplaints,
  onBulkDelete,
  onIgnoreComplaint,
  onDelete,
}: Props) => {
  if (items.length === 0) {
    return <EmptyState title="No reports in this queue" subtitle="Adjust filters to widen scope." />
  }

  return (
    <div className="stack">
      <div className="actions-row">
        <button className="button-neutral" onClick={onSelectAllVisible}>Select all visible</button>
        <button className="button-neutral" onClick={onClearSelection}>Clear selection</button>
        <span className="subtle">Selected: {selectedIds.length}</span>
      </div>
      {selectedIds.length > 0 ? (
        <div className="actions-row bulk-strip">
          <button className="button-neutral" onClick={onBulkIgnoreComplaints}>Ignore complaint (selected)</button>
          {role === 'admin' ? <button className="button-danger" onClick={onBulkDelete}>Delete post (selected)</button> : null}
        </div>
      ) : null}
      <div className="grid">
        {items.map((item) => (
          <article key={item.id} className="card stack">
            <label><input type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => onToggleSelected(item.id)} /> Select #{item.id}</label>
            <h3>#{item.id} {item.title}</h3>
            <p className="subtle">{item.category} · {item.location} · @{item.owner_telegram_username || item.telegram_username || 'n/a'}</p>
            <ModerationSignals signal={signals[item.id]} />
            <div className="status-row">
              <span className={`badge ${item.status}`}>{item.status}</span>
              <span className={`badge ${item.lifecycle}`}>{item.lifecycle}</span>
              <span className={`badge ${item.moderation_status}`}>{item.moderation_status}</span>
              {signals[item.id]?.suspicion_markers?.length ? <span className="badge flagged">high risk</span> : null}
            </div>
            <div className="actions-row">
              {item.moderation_status === 'flagged' ? (
                <button className="button-neutral" onClick={() => onIgnoreComplaint(item.id)}>Ignore complaint</button>
              ) : null}
              {role === 'admin' ? (
                <>
                  <button className="button-danger" onClick={() => onDelete(item.id)}>Delete post</button>
                </>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
