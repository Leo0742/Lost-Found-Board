import { QueuePreset } from '../../hooks/useAdminDashboard'
import { useSettings } from '../../context/SettingsContext'

const presetButtons: Array<{ preset: QueuePreset; key: string }> = [
  { preset: 'flagged', key: 'admin.preset.flagged' },
  { preset: 'suspicious', key: 'admin.preset.suspicious' },
]

export const QueuePresetControls = ({
  activePreset,
  disabled,
  onApply,
}: {
  activePreset: QueuePreset | null
  disabled?: boolean
  onApply: (preset: QueuePreset) => void
}) => {
  const { t } = useSettings()
  return (
    <div className="quick-actions">
      {presetButtons.map(({ preset, key }) => (
      <button
        key={preset}
        type="button"
        className={`button-neutral preset-button ${activePreset === preset ? 'preset-active' : ''}`.trim()}
        aria-pressed={activePreset === preset}
        disabled={disabled}
        onClick={() => onApply(preset)}
      >
        {t(key)}
      </button>
      ))}
    </div>
  )
}
