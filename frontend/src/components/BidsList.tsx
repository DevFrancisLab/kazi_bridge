import { useState } from "react";

type Bid = {
  id: number;
  freelancer: string;
  proposal: string;
  amount: string;
  rating?: number;
};

const initialBids: Bid[] = [
  {
    id: 1,
    freelancer: "Samuel N.",
    proposal: "Experienced full-stack developer ready to deliver this project in 2 weeks.",
    amount: "KES 110,000",
    rating: 4.8,
  },
  {
    id: 2,
    freelancer: "Asha M.",
    proposal: "I will design a modern UI using React and Tailwind with a strong focus on conversion.",
    amount: "KES 123,000",
    rating: 4.6,
  },
  {
    id: 3,
    freelancer: "David K.",
    proposal: "I have delivered similar platforms. Happy to provide optimization and testing.",
    amount: "KES 99,500",
    rating: 4.9,
  },
];

const BidsList = () => {
  const [bids, setBids] = useState(initialBids);

  const handleAccept = (id: number) => {
    alert(`Accepted bid ${id}`);
  };

  const handleReject = (id: number) => {
    setBids((prev) => prev.filter((bid) => bid.id !== id));
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
      <h3 className="text-lg font-semibold text-black dark:text-white">Bids for selected job</h3>
      <div className="mt-4 space-y-3">
        {bids.map((bid) => (
          <article
            key={bid.id}
            className="rounded-xl border border-gray-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md dark:border-gray-700 dark:bg-slate-900"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-base font-semibold text-slate-900 dark:text-white">{bid.freelancer}</p>
                <p className="text-sm text-gray-600 dark:text-gray-300">{bid.proposal}</p>
                <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-gray-100">Bid: {bid.amount}</p>
                {bid.rating !== undefined && (
                  <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">
                    ★ {bid.rating}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReject(bid.id)}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-gray-100 hover:text-slate-900"
                >
                  Reject
                </button>
                <button
                  onClick={() => handleAccept(bid.id)}
                  className="rounded-lg px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                  style={{ backgroundColor: '#70e000' }}
                >
                  Accept
                </button>
              </div>
            </div>
          </article>
        ))}
        {bids.length === 0 && (
          <p className="rounded-lg border border-dashed border-gray-300 p-4 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
            No bids available.
          </p>
        )}
      </div>
    </section>
  );
};

export default BidsList;
