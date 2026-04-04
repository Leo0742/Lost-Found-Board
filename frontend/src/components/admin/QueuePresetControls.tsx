import { QueuePreset } from '../../hooks/useAdminDashboard'

export const QueuePresetControls = ({ onApply }: { onApply: (preset: QueuePreset) => void }) => (
  <div className="quick-actions">
    <button onClick={() => onApply('flagged')}>Flagged priority</button>
    <button className="button-neutral" onClick={() => onApply('pending')}>Pending intake</button>
    <button className="button-neutral" onClick={() => onApply('recent')}>Recent activity</button>
    <button className="button-ghost" onClick={() => onApply('suspicious')}>Suspicious focus</button>
  </div>
)
