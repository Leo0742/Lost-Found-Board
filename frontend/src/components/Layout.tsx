import { Link, Outlet } from 'react-router-dom'

export const Layout = () => {
  return (
    <div className="app-shell">
      <header className="header">
        <div className="container">
          <Link className="brand" to="/">
            Lost & Found Board
          </Link>
          <nav>
            <Link to="/">Items</Link>
            <Link to="/new">Report Item</Link>
          </nav>
        </div>
      </header>
      <main className="container content">
        <Outlet />
      </main>
    </div>
  )
}
