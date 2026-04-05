import { ReactNode } from 'react'

export const PageHero = ({
  title,
  subtitle,
  actions,
  stats,
  compact,
}: {
  title: string
  subtitle: string
  actions?: ReactNode
  stats?: Array<{ label: string; value: string | number }>
  compact?: boolean
}) => (
  <header className={`hero hero-grid ${compact ? 'hero-compact' : ''}`}>
    <div>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      {actions ? <div className="actions-row">{actions}</div> : null}
    </div>
    {stats?.length ? (
      <div className="hero-stats hero-stats-grid">
        {stats.map((stat) => (
          <div key={stat.label}>
            <strong>{stat.value}</strong>
            <br />
            {stat.label}
          </div>
        ))}
      </div>
    ) : null}
  </header>
)

export const SectionCard = ({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}) => (
  <section className="dashboard-block stack">
    <div className="section-head">
      <div>
        <h2>{title}</h2>
        {subtitle ? <p className="subtle">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
    {children}
  </section>
)

export const EmptyState = ({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) => (
  <div className="empty-state">
    <h3>{title}</h3>
    <p>{subtitle}</p>
    {action ? <div className="actions-row" style={{ justifyContent: 'center' }}>{action}</div> : null}
  </div>
)

export const LoadingGrid = ({ count = 3, card = false }: { count?: number; card?: boolean }) => (
  <div className={card ? 'board-grid' : 'grid'}>{Array.from({ length: count }).map((_, idx) => <div className={`skeleton ${card ? 'skeleton-card' : ''}`} key={idx} />)}</div>
)
