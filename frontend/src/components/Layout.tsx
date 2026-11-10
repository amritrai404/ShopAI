import { Link, Outlet, useLocation } from 'react-router-dom'
import { LayoutDashboard, MessageCircle, Upload, TrendingUp, FileText } from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp },
  { to: '/documents', label: 'Documents', icon: FileText },
]

export default function Layout() {
  const loc = useLocation()
  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-slate-900 text-white flex flex-col">
        <div className="p-4 text-xl font-bold border-b border-slate-700">ShopAI</div>
        <nav className="flex-1 p-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-lg text-sm mb-1',
                loc.pathname === to
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-300 hover:bg-slate-800',
              )}
            >
              <Icon size={16} /> {label}
            </Link>
          ))}
        </nav>
        <div className="p-3 text-xs text-slate-400 border-t border-slate-700">
          Local AI · v0.1.0
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}