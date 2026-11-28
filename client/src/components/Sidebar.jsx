import { useState } from 'react'
import { clsx } from 'clsx'
import { NavLink } from 'react-router-dom'
import { FaArrowRightLong, FaDatabase, FaRegEye } from 'react-icons/fa6'
import { MdDashboard } from 'react-icons/md'

import logo from '../assets/logo.svg'

const navLinks = [
  {
    title: 'Dashboard',
    url: '/dashboard',
    icon: <MdDashboard aria-hidden="true" />,
  },
  {
    title: 'Top-Down View',
    url: '/topdown',
    icon: <FaRegEye aria-hidden="true" />,
  },
  {
    title: 'Database',
    url: '/database',
    icon: <FaDatabase aria-hidden="true" />,
  },
]

const Sidebar = () => {
  const [expanded, setExpanded] = useState(false)

  return (
    <aside
      className={clsx(
        'veritas-sidebar',
        expanded && 'is-expanded'
      )}
      data-expanded={expanded}
      aria-label="Main navigation"
    >
      <div className={clsx('sidebar-header', expanded ? 'justify-between' : 'justify-center')}>
        {expanded && <img src={logo} alt="Veritas" className="sidebar-logo" />}
        <button
          type="button"
          onClick={() => setExpanded(previous => !previous)}
          className="sidebar-toggle"
          aria-label={expanded ? 'Collapse navigation' : 'Expand navigation'}
          title={expanded ? 'Collapse navigation' : 'Expand navigation'}
        >
          <FaArrowRightLong className={clsx(expanded && 'rotate-180')} aria-hidden="true" />
        </button>
      </div>

      <nav className="w-full" aria-label="Pages">
        <ul className="sidebar-list">
          {navLinks.map(link => (
            <li key={link.url}>
              <NavLink
                to={link.url}
                title={expanded ? undefined : link.title}
                aria-label={link.title}
                className={({ isActive }) => clsx(
                  'sidebar-link',
                  expanded ? 'is-expanded' : 'is-collapsed',
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
                )}
              >
                <span className="sidebar-icon" aria-hidden="true">{link.icon}</span>
                {expanded && <span className="sidebar-label">{link.title}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}

export default Sidebar
