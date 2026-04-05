import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { getAuthMe } from '../api/items'
import { ThemeMode, useSettings } from '../context/SettingsContext'

const themeModes: ThemeMode[] = ['light', 'dark', 'system']

export const Layout = () => {
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null)
  const [linkedUserId, setLinkedUserId] = useState<number | null>(null)
  const [role, setRole] = useState<'admin' | 'moderator' | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const settingsRef = useRef<HTMLDivElement | null>(null)
  const { theme, setTheme, language, setLanguage, t } = useSettings()

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const me = await getAuthMe()
        if (!me.linked || !me.admin_access) {
          setRole(null)
          setLinkedUsername(null)
          setLinkedUserId(null)
          return
        }
        setRole(me.role ?? null)
        setLinkedUsername(me.identity?.telegram_username ?? null)
        setLinkedUserId(me.identity?.telegram_user_id ?? null)
      } catch {
        setRole(null)
      }
    }
    loadAuth()
  }, [])

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!settingsRef.current) return
      if (!settingsRef.current.contains(event.target as Node)) {
        setSettingsOpen(false)
      }
    }

    if (!settingsOpen) return
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [settingsOpen])

  const identityLabel = linkedUsername ? `@${linkedUsername}` : linkedUserId

  const roleLabel = useMemo(() => {
    if (role === 'admin') return t('role.admin')
    if (role === 'moderator') return t('role.moderator')
    return ''
  }, [role, t])

  return (
    <div className="app-shell">
      <header className="header">
        <div className="container">
          <Link className="brand" to="/">{t('app.title')}</Link>
          <nav className="top-nav">
            <NavLink to="/">{t('nav.items')}</NavLink>
            <NavLink to="/new">{t('nav.report')}</NavLink>
            <NavLink to="/my-reports">{t('nav.myReports')}</NavLink>
            <NavLink to="/profile">{t('nav.profile')}</NavLink>
            {role ? <NavLink to="/admin">{t('nav.moderation')}</NavLink> : null}
          </nav>
          <div className="header-right" ref={settingsRef}>
            {role ? (
              <div className={`role-chip ${role}`}>
                <span>{roleLabel}</span>
                <small>{identityLabel}</small>
              </div>
            ) : null}
            <button
              type="button"
              className="settings-trigger button-neutral"
              onClick={() => setSettingsOpen((value) => !value)}
              aria-expanded={settingsOpen}
              aria-controls="settings-panel"
              title={t('settings.title')}
            >
              <span aria-hidden="true">⚙</span>
              <span className="sr-only">{t('settings.title')}</span>
            </button>

            {settingsOpen ? (
              <div className="settings-panel" id="settings-panel">
                <h3>{t('settings.title')}</h3>
                <p className="subtle">{t('settings.subtitle')}</p>

                <div className="settings-section stack">
                  <strong>{t('settings.appearance')}</strong>
                  <label>
                    {t('settings.theme')}
                    <select value={theme} onChange={(event) => setTheme(event.target.value as ThemeMode)}>
                      {themeModes.map((mode) => (
                        <option key={mode} value={mode}>{t(`settings.theme.${mode}`)}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="settings-section stack">
                  <strong>{t('settings.language')}</strong>
                  <div className="lang-toggle" role="radiogroup" aria-label={t('settings.language')}>
                    <button
                      type="button"
                      className={`button-neutral ${language === 'en' ? 'active' : ''}`}
                      onClick={() => setLanguage('en')}
                      aria-pressed={language === 'en'}
                    >
                      {t('settings.language.en')}
                    </button>
                    <button
                      type="button"
                      className={`button-neutral ${language === 'ru' ? 'active' : ''}`}
                      onClick={() => setLanguage('ru')}
                      aria-pressed={language === 'ru'}
                    >
                      {t('settings.language.ru')}
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </header>
      <main className="container content">
        <Outlet />
      </main>
    </div>
  )
}
