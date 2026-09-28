import { useState } from "react";

type PaymentMethod = "mpesa" | "crypto";

const PaymentSection = () => {
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>("mpesa");
  const [status, setStatus] = useState<"Pending" | "Paid">("Pending");

  const freelancer = "Samuel N.";
  const amount = "KES 110,000";

  const handlePayNow = () => {
    setStatus("Paid");
    setTimeout(() => setStatus("Pending"), 0); // no-op for mock behavior
    // In real app: call payment endpoint and set status accordingly
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-black dark:text-white">Payment</h3>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            status === "Paid" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
          }`}
        >
          {status}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
          <p className="text-sm text-gray-500 dark:text-gray-300">Freelancer</p>
          <p className="text-base font-semibold text-slate-900 dark:text-white">{freelancer}</p>
        </div>
        <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
          <p className="text-sm text-gray-500 dark:text-gray-300">Agreed Amount</p>
          <p className="text-base font-semibold text-slate-900 dark:text-white">{amount}</p>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-600 dark:text-gray-300">Payment Method</p>
          <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-slate-900 ${selectedMethod === 'mpesa' ? 'bg-gray-100' : ''}">
            <input
              type="radio"
              name="payment-method"
              value="mpesa"
              checked={selectedMethod === "mpesa"}
              onChange={() => setSelectedMethod("mpesa")}
              className="h-4 w-4 text-blue-600"
            />
            <div>
              <p className="font-medium text-slate-900 dark:text-white">M-Pesa</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Mobile payment via M-Pesa</p>
            </div>
          </label>

          <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-slate-900 ${selectedMethod === 'crypto' ? 'bg-gray-100' : ''}">
            <input
              type="radio"
              name="payment-method"
              value="crypto"
              checked={selectedMethod === "crypto"}
              onChange={() => setSelectedMethod("crypto")}
              className="h-4 w-4 text-blue-600"
            />
            <div>
              <p className="font-medium text-slate-900 dark:text-white">Crypto</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Mock cryptocurrency payment</p>
            </div>
          </label>
        </div>

        <button
          onClick={handlePayNow}
          className="w-full rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: '#70e000' }}
        >
          Pay Now
        </button>
      </div>
    </section>
  );
};

export default PaymentSection;
