import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import PaymentSection from "@/components/PaymentSection";
import {
  checkPayazaPaymentStatus,
  fetchClientJobs,
  fetchPayments,
  formatPaymentAmount,
  paymentQueryKey,
  paymentStatusClass,
  paymentStatusLabel,
  readApiError,
  replacePayment,
  type Payment,
} from "@/lib/api/payments";

const PaymentsPage = () => {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const paymentsQuery = useQuery({
    queryKey: paymentQueryKey,
    queryFn: fetchPayments,
  });
  const jobsQuery = useQuery({
    queryKey: ["client-jobs"],
    queryFn: fetchClientJobs,
  });
  const statusMutation = useMutation({
    mutationFn: (paymentId: number) => checkPayazaPaymentStatus(paymentId),
    onSuccess: async (result) => {
      queryClient.setQueryData<Payment[]>(paymentQueryKey, (current) => replacePayment(current, result.payment));
      setNotice(paymentStatusLabel[result.payment.status]);
      await queryClient.invalidateQueries({ queryKey: paymentQueryKey });
    },
    onError: (error) => setNotice(readApiError(error)),
  });
  const jobsById = new Map((jobsQuery.data ?? []).map((job) => [job.id, job]));

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Client Payment History</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">
          Project payments for your jobs.
        </p>
      </div>

      <PaymentSection />

      {notice && <p className="text-sm text-slate-700 dark:text-gray-200">{notice}</p>}

      {paymentsQuery.isLoading ? (
        <p className="text-sm text-gray-500 dark:text-gray-300">Loading payments...</p>
      ) : paymentsQuery.isError ? (
        <p className="text-sm text-red-600">{readApiError(paymentsQuery.error)}</p>
      ) : (paymentsQuery.data ?? []).length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-300">No payments yet.</p>
      ) : (
        <div className="grid gap-4">
          {(paymentsQuery.data ?? []).map((payment) => {
            const job = jobsById.get(payment.job);
            const created = new Date(payment.created_at);
            const dateLabel = Number.isNaN(created.getTime())
              ? payment.created_at
              : created.toLocaleDateString();
            return (
              <article
                key={payment.id}
                className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                      {job?.title ?? `Job ${payment.job}`}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">
                      {job?.freelancer?.email ?? "Freelancer"}
                    </p>
                    <p className="mt-2 text-base font-semibold text-slate-900 dark:text-white">
                      {formatPaymentAmount(payment.amount, payment.currency)}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${paymentStatusClass[payment.status]}`}
                  >
                    {paymentStatusLabel[payment.status]}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-500 dark:text-gray-300">
                  <p>Currency: {payment.currency}</p>
                  <p>Date: {dateLabel}</p>
                  <p>Reference: {payment.transaction_reference}</p>
                </div>
                {payment.status === "PAYMENT_PROCESSING" && (
                  <button
                    type="button"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate(payment.id)}
                    className="mt-4 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    style={{ backgroundColor: "#70e000" }}
                  >
                    {statusMutation.isPending ? "Checking status..." : "Check status"}
                  </button>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default PaymentsPage;
