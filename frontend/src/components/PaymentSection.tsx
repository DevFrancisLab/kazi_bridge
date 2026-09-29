import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  checkPayazaPaymentStatus,
  createPayment,
  currentPaymentForJob,
  fetchClientJobs,
  fetchPayments,
  formatPaymentAmount,
  paymentFlowSteps,
  paymentQueryKey,
  paymentStatusClass,
  paymentStatusLabel,
  readApiError,
  replacePayment,
  startPayazaPayment,
  type ClientJobSummary,
  type Payment,
  type PaymentStatus,
} from "@/lib/api/payments";

const ACTIVE_OR_OPEN = new Set<PaymentStatus>([
  "PAYMENT_PENDING",
  "PAYMENT_PROCESSING",
  "PAYMENT_RECEIVED",
]);

const payButtonClass =
  "mt-4 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60";

function flowIndex(status: PaymentStatus | null): number {
  if (!status || status === "PAYMENT_PENDING") return 0;
  if (status === "PAYMENT_PROCESSING") return 1;
  if (status === "PAYMENT_RECEIVED") return 2;
  return -1;
}

function pickPaymentJob(jobs: ClientJobSummary[], payments: Payment[]): ClientJobSummary | null {
  const payable = jobs.filter((job) => job.status === "IN_PROGRESS" || job.status === "COMPLETED");
  const rank = (job: ClientJobSummary) => {
    const payment = currentPaymentForJob(payments, job.id);
    if (payment?.status === "PAYMENT_PROCESSING") return 0;
    if (!payment || payment.status === "PAYMENT_PENDING") return 1;
    if (payment.status === "PAYMENT_FAILED" || payment.status === "PAYMENT_CANCELLED") return 2;
    return 3;
  };
  return [...payable].sort((left, right) => rank(left) - rank(right))[0] ?? null;
}

export function ProjectPaymentCard({
  jobId,
  projectName,
  freelancerName,
  previewAmount,
}: {
  jobId: number;
  projectName: string;
  freelancerName: string;
  previewAmount?: string | number | null;
}) {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const paymentInFlight = useRef(false);
  const paymentsQuery = useQuery({
    queryKey: paymentQueryKey,
    queryFn: fetchPayments,
  });
  const listed = currentPaymentForJob(paymentsQuery.data ?? [], jobId);
  const statusQuery = useQuery({
    queryKey: ["payments", listed?.id, "payaza-status"],
    queryFn: () => checkPayazaPaymentStatus(listed!.id),
    enabled: listed?.status === "PAYMENT_PROCESSING",
    retry: false,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => {
      const status = query.state.data?.payment?.status;
      if (status && status !== "PAYMENT_PROCESSING") return false;
      if (query.state.dataUpdateCount + query.state.fetchFailureCount >= 4) return false;
      return 20000;
    },
  });
  const refreshedPayment = statusQuery.data?.payment;
  const payment =
    refreshedPayment && refreshedPayment.id === listed?.id ? refreshedPayment : listed;

  useEffect(() => {
    const updated = statusQuery.data?.payment;
    if (!updated) return;
    queryClient.setQueryData<Payment[]>(paymentQueryKey, (current) => replacePayment(current, updated));
  }, [queryClient, statusQuery.data]);

  const remember = (next: Payment) => {
    queryClient.setQueryData<Payment[]>(paymentQueryKey, (current) => replacePayment(current, next));
  };

  const payMutation = useMutation({
    mutationFn: async () => {
      const cached = () => queryClient.getQueryData<Payment[]>(paymentQueryKey) ?? [];
      let payment = currentPaymentForJob(cached(), jobId);
      if (!payment || !ACTIVE_OR_OPEN.has(payment.status)) {
        try {
          payment = await createPayment(jobId);
        } catch (error) {
          const refreshed = await fetchPayments();
          queryClient.setQueryData(paymentQueryKey, refreshed);
          const recovered = currentPaymentForJob(refreshed, jobId);
          if (!recovered || !ACTIVE_OR_OPEN.has(recovered.status)) {
            throw error;
          }
          payment = recovered;
        }
      }
      if (payment.status !== "PAYMENT_PENDING") {
        return payment;
      }
      const started = await startPayazaPayment(payment.id);
      return started.payment;
    },
    onSuccess: async (next) => {
      remember(next);
      setNotice(paymentStatusLabel[next.status]);
      await queryClient.invalidateQueries({ queryKey: paymentQueryKey });
    },
    onError: (error) => {
      setNotice(readApiError(error));
      void queryClient.invalidateQueries({ queryKey: paymentQueryKey });
    },
  });

  const statusMutation = useMutation({
    mutationFn: (paymentId: number) => checkPayazaPaymentStatus(paymentId),
    onSuccess: async (result) => {
      remember(result.payment);
      setNotice(paymentStatusLabel[result.payment.status]);
      await queryClient.invalidateQueries({ queryKey: paymentQueryKey });
    },
    onError: (error) => setNotice(readApiError(error)),
  });

  const status = payment?.status ?? null;
  const label = status ? paymentStatusLabel[status] : "Payment pending";
  const pillClass = status ? paymentStatusClass[status] : paymentStatusClass.PAYMENT_PENDING;
  const reachedIndex = flowIndex(status);
  const amountText = payment
    ? formatPaymentAmount(payment.amount, payment.currency)
    : formatPaymentAmount(previewAmount ?? 0, "KES");
  const currency = payment?.currency ?? "KES";
  const busy = payMutation.isPending || paymentsQuery.isLoading;
  const canStart = !payment || status === "PAYMENT_PENDING" || status === "PAYMENT_FAILED" || status === "PAYMENT_CANCELLED";

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-slate-800">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h4 className="text-md font-semibold text-gray-900 dark:text-white">Pay for Project</h4>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">{projectName}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${pillClass}`}>{label}</span>
      </div>

      {paymentsQuery.isError ? (
        <div className="space-y-3">
          <p className="text-sm text-red-600">{readApiError(paymentsQuery.error)}</p>
          <button
            type="button"
            onClick={() => void paymentsQuery.refetch()}
            className={payButtonClass}
            style={{ backgroundColor: "#70e000" }}
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Freelancer</p>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">{freelancerName}</p>
            </div>
            <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                {payment ? "Amount" : "Accepted bid amount"}
              </p>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">{amountText}</p>
            </div>
            <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Currency</p>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">{currency}</p>
            </div>
            <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-slate-900">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Reference</p>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">
                {payment?.transaction_reference ?? "Created when you pay"}
              </p>
            </div>
          </div>

          <ol className="mt-4 space-y-1 text-sm">
            {paymentFlowSteps.map((step, index) => (
              <li
                key={step.status}
                className={index <= reachedIndex ? "font-medium text-slate-900 dark:text-white" : "text-gray-400"}
              >
                {step.label}
              </li>
            ))}
          </ol>

          {canStart && (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                if (paymentInFlight.current || payMutation.isPending) return;
                paymentInFlight.current = true;
                setNotice(null);
                payMutation.mutate(undefined, {
                  onSettled: () => {
                    paymentInFlight.current = false;
                  },
                });
              }}
              className={payButtonClass}
              style={{ backgroundColor: "#70e000" }}
            >
              {payMutation.isPending ? "Starting payment..." : "Pay for Project"}
            </button>
          )}

          {status === "PAYMENT_PROCESSING" && (
            <button
              type="button"
              disabled={statusMutation.isPending || !payment}
              onClick={() => {
                if (!payment) return;
                setNotice(null);
                statusMutation.mutate(payment.id);
              }}
              className={payButtonClass}
              style={{ backgroundColor: "#70e000" }}
            >
              {statusMutation.isPending ? "Checking status..." : "Check status"}
            </button>
          )}

          {notice && <p className="mt-3 text-sm text-slate-700 dark:text-gray-200">{notice}</p>}
          {statusQuery.isError && (
            <p className="mt-3 text-sm text-red-600">{readApiError(statusQuery.error)}</p>
          )}
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            {status === "PAYMENT_RECEIVED"
              ? "This payment has been received."
              : status === "PAYMENT_PROCESSING"
                ? "Payment processing. Status is checked a few times, then use Check status to refresh."
                : "M-Pesa collection starts only when you choose Pay for Project."}
          </p>
        </>
      )}
    </div>
  );
}

const PaymentSection = () => {
  const paymentsQuery = useQuery({
    queryKey: paymentQueryKey,
    queryFn: fetchPayments,
  });
  const jobsQuery = useQuery({
    queryKey: ["client-jobs"],
    queryFn: fetchClientJobs,
  });

  if (paymentsQuery.isLoading || jobsQuery.isLoading) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <p className="text-sm text-gray-500 dark:text-gray-300">Loading payments...</p>
      </section>
    );
  }

  if (paymentsQuery.isError || jobsQuery.isError) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <p className="text-sm text-red-600">
          {readApiError(paymentsQuery.error ?? jobsQuery.error)}
        </p>
      </section>
    );
  }

  const job = pickPaymentJob(jobsQuery.data ?? [], paymentsQuery.data ?? []);
  if (!job) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Pay for Project</h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
          Payments appear here after a bid is accepted.
        </p>
      </section>
    );
  }

  return (
    <ProjectPaymentCard
      jobId={job.id}
      projectName={job.title}
      freelancerName={job.freelancer?.email ?? "Freelancer"}
      previewAmount={job.budget}
    />
  );
};

export default PaymentSection;
