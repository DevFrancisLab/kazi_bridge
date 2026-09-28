import { DashboardContent } from "@/components/DashboardLayout";

const EarningsPage = () => {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Earnings</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Track your income and payment history</p>
      </section>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <p className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-300">Total Earnings</p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">KES 187,200</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <p className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-300">This Month</p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">KES 45,000</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <p className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-300">Pending</p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">KES 12,500</p>
        </div>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Recent Payments</h4>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Logo Design Project</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Completed on March 15, 2026</p>
            </div>
            <span className="font-semibold text-green-600">+KES 35,000</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Website Mockups</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Completed on March 10, 2026</p>
            </div>
            <span className="font-semibold text-green-600">+KES 28,000</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Mobile App UI</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Pending payment</p>
            </div>
            <span className="font-semibold text-amber-600">KES 12,500</span>
          </div>
        </div>
      </section>
    </div>
  );
};

export default EarningsPage;