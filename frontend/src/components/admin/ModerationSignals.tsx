import { ModerationSignal } from '../../api/items'

const markerLabels: Record<string, string> = {
  flag_spike_24h: 'Flag spike in last 24h',
  high_total_flags: 'High historical flag volume',
  claim_spike_24h: 'Claim spike in last 24h',
  duplicate_flag_pressure: 'Repeated duplicate-flag pressure',
  abuse_blocks_24h: 'Recent blocked abuse events',
}

export const ModerationSignals = ({ signal }: { signal?: ModerationSignal }) => {
  if (!signal) {
    return <p className="subtle">No moderation signals yet.</p>
  }

  return (
    <div className="stack" style={{ gap: '0.35rem' }}>
      <p className="subtle">Flags: {signal.total_flags} total · {signal.recent_flags_24h} in 24h · duplicate pressure {signal.duplicate_flags_24h}</p>
      <p className="subtle">Claims: {signal.claim_count} total · {signal.recent_claims_24h} in 24h</p>
      <p className="subtle">Blocked abuse actions (24h): {signal.blocked_events_24h}</p>
      {signal.suspicion_markers.length ? (
        <div className="status-row">
          {signal.suspicion_markers.map((marker) => <span key={marker} className="badge flagged">{markerLabels[marker] ?? marker.replace(/_/g, ' ')}</span>)}
        </div>
      ) : <p className="subtle">No active risk markers.</p>}
    </div>
  )
}
