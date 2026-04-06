import { QueuePreset } from '../../hooks/useAdminDashboard'

const presetButtons: Array<{ preset: QueuePreset; label: string }> = [
  { preset: 'flagged', label: 'Flagged priority' },
  { preset: 'pending', label: 'Pending intake' },
  { preset: 'recent', label: 'Recent activity' },
  { preset: 'suspicious', label: 'Suspicious focus' },
]

export const QueuePresetControls = ({
  activePreset,
  disabled,
  onApply,
}: {
  activePreset: QueuePreset | null
  disabled?: boolean
  onApply: (preset: QueuePreset) => void
}) => (
  <div className="quick-actions">
    {presetButtons.map(({ preset, label }) => (
      <button
        key={preset}
        type="button"
        className={`button-neutral preset-button ${activePreset === preset ? 'preset-active' : ''}`.trim()}
        aria-pressed={activePreset === preset}
        disabled={disabled}
        onClick={() => onApply(preset)}
      >
        {label}
      </button>
    ))}
  </div>
)
