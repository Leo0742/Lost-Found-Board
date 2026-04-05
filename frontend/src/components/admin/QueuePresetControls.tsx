import { QueuePreset } from '../../hooks/useAdminDashboard'

const presetButtons: Array<{ preset: QueuePreset; label: string; variant: string }> = [
  { preset: 'flagged', label: 'Flagged priority', variant: '' },
  { preset: 'pending', label: 'Pending intake', variant: 'button-neutral' },
  { preset: 'recent', label: 'Recent activity', variant: 'button-neutral' },
  { preset: 'suspicious', label: 'Suspicious focus', variant: 'button-ghost' },
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
    {presetButtons.map(({ preset, label, variant }) => (
      <button
        key={preset}
        type="button"
        className={`${variant} ${activePreset === preset ? 'preset-active' : ''}`.trim()}
        aria-pressed={activePreset === preset}
        disabled={disabled}
        onClick={() => onApply(preset)}
      >
        {label}
      </button>
    ))}
  </div>
)
