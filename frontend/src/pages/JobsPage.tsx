import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJobs } from "@/lib/auth";

interface Job {
  id: number;
  title: string;
  description: string;
  budget: number;
  status: string;
  created_at: string;
}

const JobsPage = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getJobs();
      if (response.success) {
        setJobs(response.data || []);
      } else {
        setError(response.message || "Unable to load jobs.");
      }
    } catch (err) {
      setError("Unable to load jobs, please retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'OPEN':
        return 'bg-sky-100 text-sky-700';
      case 'IN_PROGRESS':
        return 'bg-amber-100 text-amber-700';
      case 'COMPLETED':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-900 dark:text-white">My Jobs</h2>

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading jobs...</p>
      ) : error ? (
        <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-gray-600 dark:text-gray-300">No jobs posted yet.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => (
            <article
              key={job.id}
              className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-gray-700 dark:bg-slate-800"
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{job.title}</h3>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusBadgeClass(job.status)}`}>
                  {job.status}
                </span>
              </div>

              <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">Budget: KES {job.budget}</p>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-300 max-w-xs truncate">
                {job.description || "No description"}
              </p>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">
                Created: {new Date(job.created_at).toLocaleDateString()}
              </p>

              <Link
                to={`/jobs/${job.id}`}
                className="mt-3 inline-block rounded-lg px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                style={{ backgroundColor: '#70e000' }}
              >
                View Details
              </Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default JobsPage;
