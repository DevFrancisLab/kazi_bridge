// import { DashboardContent } from "@/components/DashboardLayout";
import { useEffect, useState } from "react";
import api from "@/lib/api";

interface Job {
  id: number;
  title: string;
  description?: string;
  budget: number;
  deadline: string;
}

const FindJobsPage = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showBidForm, setShowBidForm] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [bidAmount, setBidAmount] = useState<number>(0);
  const [proposal, setProposal] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [submittedBids, setSubmittedBids] = useState<Set<number>>(new Set());

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await api.get("jobs/");
        console.log("API response:", response.data);
        
        // Handle different response formats
        let jobsData = [];
        if (Array.isArray(response.data)) {
          jobsData = response.data;
        } else if (response.data?.results && Array.isArray(response.data.results)) {
          jobsData = response.data.results;
        } else if (response.data?.data && Array.isArray(response.data.data)) {
          jobsData = response.data.data;
        }
        
        setJobs(jobsData);
      } catch (err) {
        console.error("Error fetching jobs:", err);
        setError("Unable to load jobs. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, []);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Find Jobs</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Browse and apply for available jobs</p>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Available Jobs</h4>
        {loading ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading jobs...</p>
        ) : error ? (
          <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
        ) : jobs.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No jobs available at the moment.</p>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md hover:-translate-y-0.5 dark:border-gray-700 dark:bg-slate-800"
              >
                <h5 className="text-base font-semibold text-gray-900 dark:text-white">{job.title}</h5>
                {job.description ? (
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{job.description}</p>
                ) : null}
                <div className="flex justify-between items-center mt-3">
                  <span className="text-sm font-medium text-green-600">KES {job.budget}</span>
                  <span className="text-sm text-slate-500 dark:text-slate-300">Deadline: {new Date(job.deadline).toLocaleDateString()}</span>
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    type="button"
                    disabled={submittedBids.has(job.id)}
                    className={`px-4 py-2 rounded-lg text-white text-sm font-medium transition ${
                      submittedBids.has(job.id)
                        ? "bg-green-500 cursor-not-allowed opacity-75"
                        : "bg-blue-600 hover:bg-blue-700"
                    }`}
                    onClick={() => {
                      setSelectedJobId(job.id);
                      setShowBidForm(true);
                      setBidAmount(job.budget);
                      setProposal("");
                      setFormError(null);
                      setFormSuccess(null);
                    }}
                  >
                    {submittedBids.has(job.id) ? "Bid Sent" : "Place Bid"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {showBidForm && selectedJobId !== null ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Place Bid</h3>
              <button
                type="button"
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-slate-300 dark:hover:text-white"
                onClick={() => setShowBidForm(false)}
              >
                Close
              </button>
            </div>

            <div className="space-y-4">
              {formError && <p className="text-sm text-red-500">{formError}</p>}
              {formSuccess && <p className="text-sm text-green-500">{formSuccess}</p>}

              <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Bid Amount</span>
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
                  value={bidAmount}
                  onChange={(e) => setBidAmount(Number(e.target.value))}
                  min={1}
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Proposal</span>
                <textarea
                  className="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
                  rows={4}
                  value={proposal}
                  onChange={(e) => setProposal(e.target.value)}
                />
              </label>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-slate-200"
                  onClick={() => setShowBidForm(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  onClick={async () => {
                    if (bidAmount <= 0 || !proposal.trim()) {
                      setFormError("Please enter valid amount and proposal.");
                      setFormSuccess(null);
                      return;
                    }

                    try {
                      await api.post("bids/", {
                        job: selectedJobId,
                        amount: bidAmount,
                        proposal,
                      });
                      setFormSuccess("Bid submitted successfully.");
                      setFormError(null);
                      setBidAmount(0);
                      setProposal("");
                      setSubmittedBids((prev) => new Set([...prev, selectedJobId]));
                      setTimeout(() => setShowBidForm(false), 1500);
                    } catch (err) {
                      console.error("Bid submission error:", err);
                      setFormError("Unable to submit bid. Please try again.");
                      setFormSuccess(null);
                    }
                  }}
                >
                  Submit Bid
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default FindJobsPage;