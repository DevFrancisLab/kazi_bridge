import { Outlet } from "react-router-dom";
import Sidebar from "@/components/Sidebar";

const DashboardShell = () => {
  return (
    <div className="min-h-screen bg-background text-foreground dark:bg-slate-950 dark:text-white">
      <Sidebar />
      <main className="dashboard-bg min-h-screen md:ml-[250px] px-4 py-6 md:px-8 md:py-8">
        <Outlet />
      </main>
    </div>
  );
};

export default DashboardShell;
