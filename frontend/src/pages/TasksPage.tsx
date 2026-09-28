import { useEffect, useState } from "react";
import api from "@/lib/api";
import { getTasks } from "@/lib/auth";

interface Task {
  id: number;
  title: string;
  description: string;
  job: {
    id: number;
    title: string;
  };
  status: string;
  created_at: string;
  updated_at: string;
}

const TasksPage = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getTasks();
      if (response.success) {
        setTasks(response.data || []);
      } else {
        setError(response.message || "Unable to load tasks.");
      }
    } catch (err) {
      setError("Unable to load tasks, please retry.");
    } finally {
      setLoading(false);
    }
  };

  const updateTaskStatus = async (
    taskId: number,
    status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED"
  ) => {
    try {
      await api.patch(`tasks/${taskId}/`, { status });
      await loadTasks();
    } catch (err) {
      console.error("Failed to update task status", err);
      setError("Failed to update task status.");
    }
  };

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">My Tasks</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Manage your assigned tasks and track progress</p>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Active Tasks</h4>

        {loading ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading tasks...</p>
        ) : error ? (
          <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-300">No tasks assigned yet.</p>
        ) : (
          <div className="space-y-4">
            {tasks.map((task) => {
              const statusBadgeClass =
                task.status === "PENDING"
                  ? "bg-amber-100 text-amber-800"
                  : task.status === "IN_PROGRESS"
                  ? "bg-blue-100 text-blue-800"
                  : task.status === "COMPLETED"
                  ? "bg-green-100 text-green-800"
                  : "bg-gray-100 text-gray-700";

              return (
                <div
                  key={task.id}
                  className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-slate-800"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h5 className="text-base font-semibold text-gray-900 dark:text-white">{task.title}</h5>
                      <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">Job: {task.job.title}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Created: {new Date(task.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${statusBadgeClass}`}>
                      {task.status}
                    </span>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {task.status === "PENDING" && (
                      <button
                        type="button"
                        onClick={() => updateTaskStatus(task.id, "IN_PROGRESS")}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                      >
                        Start
                      </button>
                    )}

                    {task.status === "IN_PROGRESS" && (
                      <button
                        type="button"
                        onClick={() => updateTaskStatus(task.id, "COMPLETED")}
                        className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                      >
                        Mark Complete
                      </button>
                    )}

                    {task.status !== "COMPLETED" && task.status !== "CANCELLED" && (
                      <button
                        type="button"
                        onClick={() => updateTaskStatus(task.id, "CANCELLED")}
                        className="px-3 py-1 border border-red-300 text-red-700 text-sm rounded hover:bg-red-50"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};

export default TasksPage;