import { useState } from "react";

const ActiveContract = () => {
  const [status, setStatus] = useState<"In Progress" | "Completed">("In Progress");

  const contract = {
    jobTitle: "React E-commerce Website",
    freelancer: "Asha M.",
    deadline: "May 22, 2026",
    status,
  };

  const handleComplete = () => {
    setStatus("Completed");
  };

  const handleRelease = () => {
    setStatus("Completed");
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Active Contract</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">Track progress and complete your contract.</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            contract.status === "In Progress" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
          }`}
        >
          {contract.status}
        </span>
      </div>

      <div className="space-y-3">
        <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Job Title</p>
          <p className="text-base font-semibold text-slate-900 dark:text-white">{contract.jobTitle}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Freelancer</p>
            <p className="text-base font-semibold text-slate-900 dark:text-white">{contract.freelancer}</p>
          </div>
          <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Deadline</p>
            <p className="text-base font-semibold text-slate-900 dark:text-white">{contract.deadline}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={handleComplete}
          className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: '#70e000' }}
        >
          Mark as Complete
        </button>
        <button
          onClick={handleRelease}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-gray-50"
        >
          Release Payment
        </button>
      </div>
    </section>
  );
};

export default ActiveContract;
