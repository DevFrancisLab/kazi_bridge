import {
  Home,
  Users,
  Bell,
  Menu,
  LogOut,
} from "lucide-react";
import { Briefcase, Clock, CheckCircle2, DollarSign } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import { getJobs, getTasks, getEarnings } from "../lib/auth";
import api from "@/lib/api";

interface Job {
  id: number;
  title: string;
  description: string;
  budget: number;
  status: string;
  created_at: string;
  updated_at: string;
  client: {
    id: number;
    email: string;
    role: string;
  };
  freelancer?: {
    id: number;
    email: string;
    role: string;
  };
}

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  job: Job;
  freelancer: {
    id: number;
    email: string;
    role: string;
  };
}

interface Earnings {
  id: number;
  amount: number;
  earned_at: string;
  job: Job;
  freelancer: {
    id: number;
    email: string;
    role: string;
  };
}

interface Bid {
  id: number;
  job: number;
  freelancer: {
    id: number;
    email: string;
    role: string;
  };
  amount: number;
  proposal: string;
  status: string;
  created_at: string;
}

interface Message {
  id: number;
  job: number;
  sender: number;
  recipient: number;
  content: string;
  created_at: string;
  is_read: boolean;
  sender_email: string;
  recipient_email: string;
}

const navItems = [
  { label: "Dashboard", icon: Home, to: "/dashboard" },
  { label: "Find Jobs", icon: Briefcase, to: "/jobs" },
  { label: "My Tasks", icon: Clock, to: "/tasks" },
  { label: "Earnings", icon: DollarSign, to: "/earnings" },
  { label: "Profile", icon: Users, to: "/profile" },
];

export const DashboardSidebar = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 w-64 overflow-y-auto border-r border-gray-200 bg-white px-4 py-6 transition-transform duration-300 ease-in-out dark:border-gray-700 dark:bg-slate-900 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      } md:translate-x-0`}
      style={{ height: "100vh" }}
    >
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-black dark:text-white">KaziBridge</h1>
        <button
          onClick={onClose}
          className="rounded-lg bg-gray-100 p-2 text-gray-700 hover:bg-gray-200 md:hidden dark:bg-slate-800 dark:text-gray-100"
          aria-label="Close sidebar"
        >
          ✕
        </button>
      </div>

      <nav className="space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.label}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-gray-100 text-black border-l-4 border-black'
                    : 'text-gray-700 hover:bg-gray-100 hover:text-black'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-gray-200 pt-5">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-gray-200" />
            <div>
              <p className="text-sm font-semibold text-gray-900">Jane Doe</p>
              <p className="text-xs text-gray-500">Freelancer</p>
            </div>
          </div>
          <button className="mt-4 w-full rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200">
            View Profile
          </button>
        </div>
        <button className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">
          <LogOut className="h-4 w-4" /> Logout
        </button>
      </div>
    </aside>
  );
};

export const DashboardTopbar = ({ onOpenSidebar }: { onOpenSidebar: () => void }) => {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 shadow-sm dark:border-gray-700 dark:bg-slate-900">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="rounded-lg bg-gray-100 p-2 text-gray-700 hover:bg-gray-200 md:hidden dark:bg-slate-800 dark:text-gray-100"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h2 className="text-xl font-semibold text-black dark:text-white">Overview</h2>
      </div>

      <div className="flex items-center gap-4">
        <button className="rounded-lg bg-gray-100 p-2 text-gray-700 hover:bg-gray-200 dark:bg-slate-800 dark:text-gray-100" aria-label="Notifications">
          <Bell className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 p-1" />
          <div>
            <p className="text-sm font-semibold text-black dark:text-white">Jane Doe</p>
            <p className="text-xs text-gray-500 dark:text-gray-300">Product Lead</p>
          </div>
        </div>
      </div>
    </header>
  );
};

export const DashboardContent = () => {
  const role = localStorage.getItem('role');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [earnings, setEarnings] = useState<Earnings[]>([]);
  const [loading, setLoading] = useState(true);
  const [bids, setBids] = useState<Bid[]>([]);
  const [bidsLoading, setBidsLoading] = useState(false);
  const [bidsError, setBidsError] = useState<string | null>(null);
  const [showPostJobForm, setShowPostJobForm] = useState(false);
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [jobBudget, setJobBudget] = useState<number>(0);
  const [jobDeadline, setJobDeadline] = useState("");
  const [postJobLoading, setPostJobLoading] = useState(false);
  const [postJobError, setPostJobError] = useState<string | null>(null);
  const [myBids, setMyBids] = useState<Bid[]>([]);
  const [myBidsLoading, setMyBidsLoading] = useState(false);
  const [selectedJobDetails, setSelectedJobDetails] = useState<Job | null>(null);
  const [jobMessages, setJobMessages] = useState<Message[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [newMessage, setNewMessage] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);

  console.log("DashboardContent rendered, role:", role);

  const fetchClientJobs = async () => {
    try {
      const jobsResponse = await getJobs();
      if (jobsResponse.success) {
        setJobs(jobsResponse.data || []);
      }
    } catch (error) {
      console.error("Error refreshing client jobs:", error);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        if (role === 'CLIENT') {
          await fetchClientJobs();
        } else if (role === 'FREELANCER') {
          const [tasksResponse, earningsResponse] = await Promise.all([
            getTasks(),
            getEarnings()
          ]);
          if (tasksResponse.success) {
            setTasks(tasksResponse.data || []);
          }
          if (earningsResponse.success) {
            setEarnings(earningsResponse.data || []);
          }
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [role]);

  // Set up polling for real-time updates
  useEffect(() => {
    if (role === 'CLIENT') {
      const pollInterval = setInterval(fetchClientJobs, 5000);
      return () => clearInterval(pollInterval);
    } else if (role === 'FREELANCER') {
      fetchMyBids();
      fetchTasksForFreelancer();
      
      const pollInterval = setInterval(() => {
        fetchMyBids();
        fetchTasksForFreelancer();
      }, 5000);
      
      return () => clearInterval(pollInterval);
    }
  }, [role]);

  const fetchBids = async (jobId: number) => {
    setBidsLoading(true);
    setBidsError(null);
    try {
      const response = await api.get(`jobs/${jobId}/bids/`);
      // Handle paginated response format
      const bidsData = Array.isArray(response.data) 
        ? response.data 
        : response.data?.results || response.data?.data || [];
      setBids(bidsData);
    } catch (error) {
      setBidsError("Unable to load bids for this job.");
      setBids([]);
    } finally {
      setBidsLoading(false);
    }
  };

  const handleJobClick = (jobId: number) => {
    setSelectedJobId(jobId);
    fetchBids(jobId);
  };

  const handleBidAction = async (bidId: number, action: 'ACCEPTED' | 'REJECTED') => {
    try {
      await api.patch(`bids/${bidId}/`, { status: action });
      setBids((prev) => prev.map((bid) => bid.id === bidId ? { ...bid, status: action } : bid));
    } catch (error) {
      setBidsError(`Failed to ${action.toLowerCase()} bid.`);
    }
  };

  const handleViewJobDetails = async (job: Job) => {
    setSelectedJobDetails(job);
    if (job.status === 'OPEN') {
      await fetchBids(job.id);
    } else {
      await fetchJobMessages(job.id);
    }
  };

  const fetchJobMessages = async (jobId: number) => {
    setMessagesLoading(true);
    try {
      const response = await api.get(`jobs/${jobId}/messages/`);
      const messagesData = Array.isArray(response.data) 
        ? response.data 
        : response.data?.results || response.data?.data || [];
      setJobMessages(messagesData);
    } catch (error) {
      console.error("Error fetching messages:", error);
      setJobMessages([]);
    } finally {
      setMessagesLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedJobDetails) return;

    setSendingMessage(true);
    try {
      const freelancer = selectedJobDetails.freelancer;
      if (!freelancer) return;

      await api.post(`jobs/${selectedJobDetails.id}/messages/`, {
        recipient: freelancer.id,
        content: newMessage.trim(),
      });

      setNewMessage("");
      await fetchJobMessages(selectedJobDetails.id);
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setSendingMessage(false);
    }
  };

  const handlePostJob = async () => {
    setPostJobError(null);

    if (!jobTitle.trim() || !jobDescription.trim() || jobBudget <= 0 || !jobDeadline) {
      setPostJobError("Please fill in all fields with valid values.");
      return;
    }

    setPostJobLoading(true);
    try {
      const response = await api.post("jobs/", {
        title: jobTitle,
        description: jobDescription,
        budget: jobBudget,
        deadline: jobDeadline,
      });

      // Refresh jobs list to ensure consistency
      await fetchClientJobs();

      // Reset form
      setJobTitle("");
      setJobDescription("");
      setJobBudget(0);
      setJobDeadline("");
      setShowPostJobForm(false);
    } catch (error) {
      const err = error as { response?: { data?: { message?: string } } };
      setPostJobError(err.response?.data?.message || "Failed to post job.");
    } finally {
      setPostJobLoading(false);
    }
  };

  const fetchMyBids = async () => {
    setMyBidsLoading(true);
    try {
      const response = await api.get("bids/");
      // Handle paginated response format
      const bidsData = Array.isArray(response.data) 
        ? response.data 
        : response.data?.results || response.data?.data || [];
      setMyBids(bidsData);
    } catch (error) {
      console.error("Error fetching my bids:", error);
      setMyBids([]);
    } finally {
      setMyBidsLoading(false);
    }
  };

  const fetchTasksForFreelancer = async () => {
    try {
      const tasksResponse = await getTasks();
      if (tasksResponse.success) {
        setTasks(tasksResponse.data || []);
      }
    } catch (error) {
      console.error("Error refreshing tasks:", error);
    }
  };

  const updateTaskStatus = async (taskId: number, status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED') => {
    try {
      await api.patch(`tasks/${taskId}/`, { status });
      fetchTasksForFreelancer();
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };

  if (loading) {
    return (
      <main className="space-y-6 p-4 md:p-6">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-24 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Summary</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              title: "Total Earnings",
              value: "$18,720",
              icon: DollarSign,
              iconColor: "text-green-500",
            },
            {
              title: "Active Jobs",
              value: "12",
              icon: Briefcase,
              iconColor: "text-blue-500",
            },
            {
              title: "Pending Payments",
              value: "4",
              icon: Clock,
              iconColor: "text-amber-500",
            },
            {
              title: "Workload Status",
              value: "Busy",
              icon: CheckCircle2,
              iconColor: "text-indigo-500",
            },
          ].map((card) => {
            const CardIcon = card.icon;
            return (
              <div
                key={card.title}
                className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-gray-700 dark:bg-slate-800"
              >
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-300">{card.title}</p>
                  <div className={`rounded-md bg-gray-100 p-2 ${card.iconColor}`}>
                    <CardIcon className="h-4 w-4" />
                  </div>
                </div>
                <p className="mt-4 text-3xl font-bold text-black dark:text-white">{card.value}</p>
              </div>
            );
          })}
        </div>
      </section>

      {role === 'CLIENT' && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-black dark:text-white">My Jobs</h3>
            <button
              type="button"
              onClick={() => setShowPostJobForm(true)}
              className="inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
              style={{ backgroundColor: '#70e000' }}
            >
              Post Job
            </button>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {jobs.length > 0 ? jobs.map((job: Job) => (
              <article
                key={job.id}
                className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-gray-700 dark:bg-slate-800"
              >
                <div className="mb-3 flex items-center justify-between">
                  <h4 className="text-base font-semibold text-slate-900 dark:text-white">{job.title}</h4>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      job.status === "OPEN"
                        ? "bg-sky-100 text-sky-700"
                        : job.status === "IN_PROGRESS"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {job.status}
                  </span>
                </div>

                <p className="mb-2 text-sm text-slate-500 dark:text-gray-300">Budget: KES {job.budget}</p>
                <p className="mb-4 text-sm text-slate-500 dark:text-gray-300">Description: {job.description.substring(0, 100)}...</p>

                <div className="flex flex-wrap gap-2">
                  <button 
                    onClick={() => handleViewJobDetails(job)}
                    className="inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:opacity-90" 
                    style={{ backgroundColor: '#70e000' }}>
                    View Details
                  </button>
                  <button className="inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:bg-slate-900 dark:text-gray-100 dark:hover:bg-slate-800">
                    Edit Job
                  </button>
                </div>
              </article>
            )) : (
              <div className="col-span-full text-center py-8">
                <p className="text-gray-500 dark:text-gray-400">No jobs posted yet.</p>
                <button 
                  type="button"
                  onClick={() => setShowPostJobForm(true)}
                  className="mt-2 inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium text-white transition hover:opacity-90" 
                  style={{ backgroundColor: '#70e000' }}>
                  Post Your First Job
                </button>
              </div>
            )}
          </div>
        </section>
      )}

      {role === 'FREELANCER' && (
        <>
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-black dark:text-white">My Bids</h3>
              <span className="text-sm text-gray-500 dark:text-gray-400">Track your submissions</span>
            </div>

            <div className="space-y-3">
              {myBidsLoading ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading bids...</p>
              ) : myBids.length > 0 ? myBids.map((bid: Bid) => {
                const statusClasses =
                  bid.status === 'PENDING'
                    ? 'bg-amber-100 text-amber-700'
                    : bid.status === 'ACCEPTED'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700';

                return (
                  <article
                    key={bid.id}
                    className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-gray-700 dark:bg-slate-800"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h4 className="text-base font-semibold text-gray-900 dark:text-white">Job #{bid.job}</h4>
                        <p className="text-sm text-gray-500 dark:text-gray-300">Amount: KES {bid.amount}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-300 max-w-xs truncate">Proposal: {bid.proposal}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-300">Submitted: {new Date(bid.created_at).toLocaleDateString()}</p>
                      </div>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${statusClasses}`}>
                        {bid.status}
                      </span>
                    </div>
                  </article>
                );
              }) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400">No bids submitted yet.</p>
                </div>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-black dark:text-white">My Tasks</h3>
              <span className="text-sm text-gray-500 dark:text-gray-400">Prioritize your work</span>
            </div>

            <div className="space-y-3">
              {tasks.length > 0 ? tasks.map((task: Task) => {
                const priorityClasses =
                  task.status === 'PENDING'
                    ? 'bg-rose-100 text-rose-700'
                    : task.status === 'IN_PROGRESS'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700';

                return (
                  <article
                    key={task.id}
                    className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-gray-700 dark:bg-slate-800"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h4 className="text-base font-semibold text-gray-900 dark:text-white">{task.title}</h4>
                        <p className="text-sm text-gray-500 dark:text-gray-300">Job: {task.job.title}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-300">Created: {new Date(task.created_at).toLocaleDateString()}</p>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${priorityClasses}`}>
                        {task.status}
                      </span>
                    </div>
                    <div className="mt-4 flex gap-2">
                      {task.status === 'PENDING' && (
                        <button
                          type="button"
                          onClick={() => updateTaskStatus(task.id, 'IN_PROGRESS')}
                          className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                        >
                          Start
                        </button>
                      )}
                      {task.status === 'IN_PROGRESS' && (
                        <button
                          type="button"
                          onClick={() => updateTaskStatus(task.id, 'COMPLETED')}
                          className="rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700"
                        >
                          Mark Complete
                        </button>
                      )}
                      {task.status !== 'COMPLETED' && task.status !== 'CANCELLED' && (
                        <button
                          type="button"
                          onClick={() => updateTaskStatus(task.id, 'CANCELLED')}
                          className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </article>
                );
              }) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400">No tasks assigned yet.</p>
                </div>
              )}
            </div>
          </section>
        </>
      )}

      {showPostJobForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Post New Job</h3>
              <button
                type="button"
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-slate-300 dark:hover:text-white"
                onClick={() => setShowPostJobForm(false)}
              >
                Close
              </button>
            </div>

            <div className="space-y-4">
              {postJobError && <p className="text-sm text-red-500">{postJobError}</p>}

              <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Job Title</span>
                <input
                  type="text"
                  className="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g., Build responsive website"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Description</span>
                <textarea
                  className="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
                  rows={3}
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Describe the job in detail..."
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Budget (KES)</span>
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
                  value={jobBudget}
                  onChange={(e) => setJobBudget(Number(e.target.value))}
                  min={1}
                  placeholder="e.g., 50000"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Deadline</span>
                <input
                  type="date"
                  className="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
                  value={jobDeadline}
                  onChange={(e) => setJobDeadline(e.target.value)}
                />
              </label>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-slate-200"
                  onClick={() => setShowPostJobForm(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={postJobLoading}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  onClick={handlePostJob}
                >
                  {postJobLoading ? "Posting..." : "Post Job"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {selectedJobDetails !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-4xl max-h-[90vh] rounded-2xl bg-white overflow-y-auto shadow-xl dark:bg-slate-900">
            <div className="sticky top-0 bg-white dark:bg-slate-900 p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Job Details: {selectedJobDetails.title}
                </h3>
                <button
                  type="button"
                  className="text-sm text-gray-500 hover:text-gray-700 dark:text-slate-300 dark:hover:text-white"
                  onClick={() => setSelectedJobDetails(null)}
                >
                  Close
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Job Card Style Information */}
              <div className="bg-gray-50 dark:bg-slate-800 p-4 rounded-lg">
                <div className="mb-3 flex items-center justify-between">
                  <h4 className="text-base font-semibold text-slate-900 dark:text-white">{selectedJobDetails.title}</h4>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      selectedJobDetails.status === "OPEN"
                        ? "bg-sky-100 text-sky-700"
                        : selectedJobDetails.status === "IN_PROGRESS"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {selectedJobDetails.status}
                  </span>
                </div>

                <p className="mb-2 text-sm text-slate-500 dark:text-gray-300">Budget: KES {selectedJobDetails.budget}</p>
                <p className="mb-4 text-sm text-slate-500 dark:text-gray-300">Description: {selectedJobDetails.description}</p>
                <p className="text-sm text-slate-500 dark:text-gray-300">Created: {new Date(selectedJobDetails.created_at).toLocaleDateString()}</p>
                {selectedJobDetails.freelancer && (
                  <p className="text-sm text-slate-500 dark:text-gray-300">Freelancer: {selectedJobDetails.freelancer.email}</p>
                )}
              </div>

              {/* Bids or Messages Section */}
              {selectedJobDetails.status === 'OPEN' ? (
                <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-4">Bids for this Job</h4>
                  
                  {/* Bids List */}
                  <div className="space-y-3 max-h-60 overflow-y-auto">
                    {bidsLoading ? (
                      <p className="text-sm text-gray-500">Loading bids...</p>
                    ) : bids.length === 0 ? (
                      <p className="text-sm text-gray-500">No bids yet.</p>
                    ) : (
                      bids.map((bid) => (
                        <div
                          key={bid.id}
                          className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-slate-800"
                        >
                          <div className="mb-3 flex items-start justify-between">
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white">
                                {bid.freelancer.email}
                              </p>
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                Bid Amount: KES {bid.amount}
                              </p>
                            </div>
                            <span
                              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                                bid.status === 'PENDING'
                                  ? 'bg-amber-100 text-amber-700'
                                  : bid.status === 'ACCEPTED'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-red-100 text-red-700'
                              }`}
                            >
                              {bid.status}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
                            {bid.proposal}
                          </p>
                          {bid.status === 'PENDING' && (
                            <div className="flex gap-2">
                              <button
                                type="button"
                                className="flex-1 rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700"
                                onClick={() => handleBidAction(bid.id, 'ACCEPTED')}
                              >
                                Accept
                              </button>
                              <button
                                type="button"
                                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-slate-800"
                                onClick={() => handleBidAction(bid.id, 'REJECTED')}
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-4">Messages with Freelancer</h4>
                  
                  {/* Messages List */}
                  <div className="space-y-3 max-h-60 overflow-y-auto mb-4">
                    {messagesLoading ? (
                      <p className="text-sm text-gray-500">Loading messages...</p>
                    ) : jobMessages.length === 0 ? (
                      <p className="text-sm text-gray-500">No messages yet. Start the conversation!</p>
                    ) : (
                      jobMessages.map((message) => (
                        <div
                          key={message.id}
                          className={`p-3 rounded-lg ${
                            message.sender_email === localStorage.getItem('email')
                              ? 'bg-blue-100 dark:bg-blue-900 ml-8'
                              : 'bg-gray-100 dark:bg-gray-700 mr-8'
                          }`}
                        >
                          <div className="flex justify-between items-start mb-1">
                            <p className="text-xs font-medium text-gray-600 dark:text-gray-300">
                              {message.sender_email}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {new Date(message.created_at).toLocaleString()}
                            </p>
                          </div>
                          <p className="text-sm text-gray-800 dark:text-gray-200">{message.content}</p>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Send Message Input */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type your message..."
                      className="flex-1 rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500 dark:border-gray-600 dark:bg-slate-700 dark:text-white"
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={sendingMessage || !newMessage.trim()}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {sendingMessage ? 'Sending...' : 'Send'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-black">KaziLink AI Assistant</h3>
          <span className="text-xs text-gray-500">Smart suggestions</span>
        </div>
        <div className="space-y-3">
          <div className="rounded-xl bg-gray-50 p-4 shadow-xs">
            <p className="text-sm font-medium text-gray-700">Task priority recommendation</p>
            <p className="mt-1 text-sm text-gray-600">Focus on Logo Design (due tomorrow)</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-4 shadow-xs">
            <p className="text-sm font-medium text-gray-700">Workload warning</p>
            <p className="mt-1 text-sm text-gray-600">You have 3 deadlines this week</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-4 shadow-xs">
            <p className="text-sm font-medium text-gray-700">Productivity tip</p>
            <p className="mt-1 text-sm text-gray-600">Complete 2 tasks today</p>
          </div>
        </div>
      </section>
    </main>
  );
};

const DashboardLayout = () => {
  return (
    <div className="min-h-screen flex flex-col font-sans text-black dark:bg-slate-950 dark:text-white">
      <DashboardTopbar onOpenSidebar={() => {}} />

      <div className="flex-1 overflow-y-auto scrollbar-hide">
        <div className="h-full">
          <div className="mx-auto w-full max-w-7xl px-0 md:px-4 p-0 md:p-4">
            <DashboardContent />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardLayout;
