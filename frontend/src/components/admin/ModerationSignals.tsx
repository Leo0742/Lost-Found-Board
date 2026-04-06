import { ModerationSignal } from '../../api/items'
import { useSettings } from '../../context/SettingsContext'

const markerLabelKeys: Record<string, string> = {
  flag_spike_24h: 'admin.signals.marker.flagSpike24h',
  high_total_flags: 'admin.signals.marker.highTotalFlags',
  claim_spike_24h: 'admin.signals.marker.claimSpike24h',
  duplicate_flag_pressure: 'admin.signals.marker.duplicatePressure',
  abuse_blocks_24h: 'admin.signals.marker.abuseBlocks24h',
}

export const ModerationSignals = ({ signal }: { signal?: ModerationSignal }) => {
  const { t } = useSettings()
  if (!signal) {
    return <p className="subtle">{t('admin.signals.empty')}</p>
  }

  return (
    <div className="stack" style={{ gap: '0.35rem' }}>
      <p className="subtle">{t('admin.signals.flags', { total: signal.total_flags, recent: signal.recent_flags_24h, duplicate: signal.duplicate_flags_24h })}</p>
      <p className="subtle">{t('admin.signals.claims', { total: signal.claim_count, recent: signal.recent_claims_24h })}</p>
      <p className="subtle">{t('admin.signals.abuseBlocked', { count: signal.blocked_events_24h })}</p>
      {signal.suspicion_markers.length ? (
        <div className="status-row">
          {signal.suspicion_markers.map((marker) => <span key={marker} className="badge flagged">{t(markerLabelKeys[marker] ?? marker.replace(/_/g, ' '))}</span>)}
        </div>
      ) : <p className="subtle">{t('admin.signals.noMarkers')}</p>}
    </div>
  )
}
