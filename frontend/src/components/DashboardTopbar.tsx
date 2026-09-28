import { Bell, Search } from "lucide-react";

const DashboardTopbar = () => {
  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 shadow-sm">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search…"
            className="h-10 w-64 rounded-lg border border-gray-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <button
          type="button"
          className="rounded-lg bg-gray-100 p-2 text-gray-500 transition hover:bg-gray-200 hover:text-slate-700"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
        </button>

        <button type="button" className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-200 text-slate-700">
          AJ
        </button>
      </div>
    </header>
  );
};

export default DashboardTopbar;
