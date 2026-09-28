import { useParams } from "react-router-dom";
import BidsList from "@/components/BidsList";

const JobDetailsPage = () => {
  const { id } = useParams();
  return (
    <section className="space-y-5">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Job Details</h2>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">Viewing job ID: {id}</p>
        <div className="mt-4 space-y-2">
          <p className="text-base font-semibold text-slate-900 dark:text-white">React E-commerce Website</p>
          <p className="text-sm text-gray-500 dark:text-gray-300">Budget: KES 250,000</p>
          <p className="text-sm text-gray-500 dark:text-gray-300">Status: In Progress</p>
          <p className="text-sm text-gray-500 dark:text-gray-300">Deadline: June 3, 2026</p>
        </div>
      </div>
      <BidsList />
    </section>
  );
};

export default JobDetailsPage;
