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
  onBulkApprove: () => void
  onBulkReject: () => void
  onBulkFlag: () => void
  onBulkUnflag: () => void
  onBulkVerify: (isVerified: boolean) => void
  onBulkLifecycle: (action: 'resolve' | 'reopen') => void
  onApprove: (itemId: number) => void
  onReject: (itemId: number) => void
  onFlag: (itemId: number) => void
  onVerifyToggle: (itemId: number, isVerified: boolean) => void
  onResolve: (itemId: number) => void
  onReopen: (itemId: number) => void
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
  onBulkApprove,
  onBulkReject,
  onBulkFlag,
  onBulkUnflag,
  onBulkVerify,
  onBulkLifecycle,
  onApprove,
  onReject,
  onFlag,
  onVerifyToggle,
  onResolve,
  onReopen,
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
          <button onClick={onBulkApprove}>Bulk approve</button>
          <button className="button-neutral" onClick={onBulkReject}>Bulk reject</button>
          <button className="button-ghost" onClick={onBulkFlag}>Bulk flag</button>
          <button className="button-neutral" onClick={onBulkUnflag}>Bulk unflag</button>
          {role === 'admin' ? (
            <>
              <button onClick={() => onBulkVerify(true)}>Bulk verify</button>
              <button className="button-neutral" onClick={() => onBulkVerify(false)}>Bulk unverify</button>
              <button onClick={() => onBulkLifecycle('resolve')}>Bulk resolve</button>
              <button className="button-neutral" onClick={() => onBulkLifecycle('reopen')}>Bulk reopen</button>
            </>
          ) : null}
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
              <button onClick={() => onApprove(item.id)}>Approve</button>
              <button className="button-neutral" onClick={() => onReject(item.id)}>Reject</button>
              <button className="button-ghost" onClick={() => onFlag(item.id)}>Flag</button>
              {role === 'admin' ? (
                <>
                  <button onClick={() => onVerifyToggle(item.id, !item.is_verified)}>{item.is_verified ? 'Unverify' : 'Verify'}</button>
                  <button onClick={() => onResolve(item.id)}>Resolve</button>
                  <button className="button-neutral" onClick={() => onReopen(item.id)}>Reopen</button>
                  <button className="button-danger" onClick={() => onDelete(item.id)}>Delete</button>
                </>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
