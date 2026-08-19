import { NavLink } from 'react-router-dom'
import './Tabs.css'

export interface TabItem {
  to: string
  label: string
  end?: boolean
}

export default function Tabs({ items }: { items: TabItem[] }) {
  return (
    <nav className="gc-tabs">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `gc-tab${isActive ? ' is-active' : ''}`}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}
