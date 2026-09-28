import { useEffect, useState } from "react";
import { getFreelancers } from "@/lib/auth";

interface Freelancer {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

const FreelancersPage = () => {
  const [freelancers, setFreelancers] = useState<Freelancer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFreelancers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getFreelancers();
      if (response.success) {
        setFreelancers(response.data || []);
      } else {
        setError(response.message || "Unable to load freelancers.");
      }
    } catch (err) {
      setError("Unable to load freelancers, please retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFreelancers();
    const interval = setInterval(loadFreelancers, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Freelancers</h2>

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading freelancers...</p>
      ) : error ? (
        <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
      ) : freelancers.length === 0 ? (
        <p className="text-sm text-gray-600 dark:text-gray-300">No freelancers available.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {freelancers.map((freelancer) => (
            <article
              key={freelancer.id}
              className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-gray-700 dark:bg-slate-800"
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{freelancer.email}</h3>
                <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700">
                  {freelancer.role}
                </span>
              </div>

              <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">
                Joined: {new Date(freelancer.created_at).toLocaleDateString()}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default FreelancersPage;