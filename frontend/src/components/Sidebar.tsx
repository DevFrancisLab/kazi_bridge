import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  Home,
  Briefcase,
  Users,
  CreditCard,
  MessageCircle,
  LogOut,
} from "lucide-react";

interface NavItem {
  key: string;
  name: string;
  icon: React.ElementType;
  path: string;
}
const clientMenu: NavItem[] = [
  { key: 'dashboard', path: '/client-dashboard', name: 'Dashboard', icon: Home },
  { key: 'my-jobs', path: '/jobs', name: 'My Jobs', icon: Briefcase },
  { key: 'freelancers', path: '/freelancers', name: 'Freelancers', icon: Users },
  { key: 'payments', path: '/payments', name: 'Payments', icon: CreditCard },
  { key: 'messages', path: '/messages', name: 'Messages', icon: MessageCircle },
];

const freelancerMenu: NavItem[] = [
  { key: 'dashboard', path: '/freelancer-dashboard', name: 'Dashboard', icon: Home },
  { key: 'find-jobs', path: '/find-jobs', name: 'Find Jobs', icon: Briefcase },
  { key: 'my-tasks', path: '/tasks', name: 'My Tasks', icon: Users },
  { key: 'earnings', path: '/earnings', name: 'Earnings', icon: CreditCard },
  { key: 'profile', path: '/profile', name: 'Profile', icon: MessageCircle },
];

const Sidebar = () => {
  const navigate = useNavigate();
  const auth = useAuth();
  const userEmail = auth.user?.email || auth.user?.name || 'Unknown User';
  const userRole = auth.user?.role || 'Unknown Role';

  // Get role from localStorage or auth context
  const localStorageRoleRaw = localStorage.getItem('role');
  const localStorageRole = (localStorageRoleRaw === 'CLIENT' || localStorageRoleRaw === 'FREELANCER') ? localStorageRoleRaw : null;
  const authRole = auth.role;

  // Debug logging
  console.log("Sidebar role debugging:");
  console.log("  localStorage raw:", localStorageRoleRaw);
  console.log("  localStorage parsed:", localStorageRole);
  console.log("  auth.role:", authRole);
  console.log("  auth.user?.role:", auth.user?.role);

  // Determine the effective role - prefer localStorage if valid, otherwise use auth.role
  const role = localStorageRole || (authRole && authRole.length > 0 ? authRole : null);

  console.log("  final role used:", role);

  // Default to client menu if role is undefined/null
  const navItems = role === 'FREELANCER' ? freelancerMenu : clientMenu;

  console.log("  selected menu:", role === 'FREELANCER' ? 'freelancerMenu' : 'clientMenu');
  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[250px] border-r border-gray-200 bg-white px-4 py-6 shadow-sm">
      <div className="mb-8 flex items-center gap-2 border-b border-gray-100 pb-5">
        <div className="h-9 w-9 rounded-md bg-gradient-to-br from-blue-600 to-cyan-500" />
        <h1 className="text-xl font-extrabold tracking-tight text-slate-900">KaziBridge</h1>
      </div>

      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition ${
                  isActive ? "bg-gray-100 font-semibold text-slate-900" : "text-slate-600 hover:bg-gray-100 hover:text-slate-900"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {item.name}
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-gray-100 pt-4">
        <div className="flex items-center gap-3 rounded-xl bg-gray-50 px-3 py-3">
          <div className="h-9 w-9 rounded-full bg-slate-300" />
          <div>
            <p className="text-sm font-semibold text-slate-900">{userEmail}</p>
            <p className="text-xs text-slate-500">{userRole}</p>
          </div>
        </div>

        <button
          onClick={async () => {
              auth.logout();
            navigate('/login');
          }}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-gray-100 hover:text-slate-900"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
