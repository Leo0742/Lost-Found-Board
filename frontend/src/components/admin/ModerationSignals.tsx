import { ModerationSignal } from '../../api/items'

export const ModerationSignals = ({ signal }: { signal?: ModerationSignal }) => {
  if (!signal) {
    return <p className="subtle">No moderation signals yet.</p>
  }

  return (
    <div className="stack" style={{ gap: '0.35rem' }}>
      <p className="subtle">Flags: {signal.total_flags} total · {signal.recent_flags_24h} recent · dupes {signal.duplicate_flags_24h}</p>
      <p className="subtle">Claim pressure: {signal.claim_count} total · {signal.recent_claims_24h} in 24h</p>
      <p className="subtle">Abuse blocks 24h: {signal.blocked_events_24h}</p>
      {signal.suspicion_markers.length ? (
        <div className="status-row">
          {signal.suspicion_markers.map((marker) => <span key={marker} className="badge flagged">{marker.replace(/_/g, ' ')}</span>)}
        </div>
      ) : null}
    </div>
  )
}
