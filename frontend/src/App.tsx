import { NavLink, Route, Routes } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import ReportsPage from './pages/ReportsPage'
import './App.css'

function navClass(isActive: boolean): string {
  return isActive ? 'nav-link is-active' : 'nav-link'
}

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Agentic Crawler</h1>
        <nav className="app-nav" aria-label="Main">
          <NavLink to="/" end className={({ isActive }) => navClass(isActive)}>
            Chat
          </NavLink>
          <NavLink
            to="/reports"
            className={({ isActive }) => navClass(isActive)}
          >
            Reports
          </NavLink>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/reports" element={<ReportsPage />} />
      </Routes>
    </div>
  )
}
