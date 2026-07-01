import { NavLink, Outlet } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, Package, Store, BarChart2,
  Activity, Search, LogOut, Zap,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

const navItems = [
  { to: '/',          icon: LayoutDashboard, label: 'Overview' },
  { to: '/products',  icon: Package,         label: 'Products' },
  { to: '/sellers',   icon: Store,           label: 'Sellers' },
  { to: '/analytics', icon: BarChart2,       label: 'Analytics' },
  { to: '/jobs',      icon: Activity,        label: 'Jobs' },
  { to: '/scraping',  icon: Search,          label: 'Scraping' },
]

export function AppLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex h-screen bg-surface-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 flex flex-col bg-surface-900 border-r border-surface-800">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-surface-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-tight">Scraping</p>
            <p className="text-xs text-slate-400 leading-tight">Platform</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-surface-800',
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-3 pb-4 border-t border-surface-800 pt-4">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
            <div className="h-7 w-7 rounded-full bg-brand-600 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-white">
                {user?.email?.[0]?.toUpperCase() ?? '?'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-300 truncate">{user?.email ?? 'User'}</p>
              <p className="text-xs text-slate-500 capitalize">{user?.role ?? ''}</p>
            </div>
            <button
              onClick={logout}
              className="text-slate-500 hover:text-slate-300 transition-colors"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
