import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  checkPayazaPayoutStatus,
  createPayout,
  currentPayoutForPayment,
  earningsQueryKey,
  fetchEarnings,
  fetchPayments,
  fetchPayouts,
  formatPaymentAmount,
  formatSummaryAmount,
  paymentForEarning,
  paymentQueryKey,
  paymentStatusClass,
  paymentStatusLabel,
  payoutQueryKey,
  payoutStatusClass,
  payoutStatusLabel,
  readApiError,
  readPayoutError,
  replacePayout,
  startPayazaPayout,
  summarizeEarnings,
  type Earning,
  type Payment,
  type Payout,
} from "@/lib/api/payments";

const actionButtonClass =
  "rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60";

function destinationName(country: string): string {
  if (country === "KE") return "Kenya";
  return country;
}

function payoutMethodName(method: string): string {
  if (method === "MOBILE_MONEY") return "Mobile Money";
  if (method === "BANK_TRANSFER") return "Bank transfer";
  return method;
}

function PayoutDestination({
  country,
  currency,
  method,
}: {
  country: string;
  currency: string;
  method: string;
}) {
  return (
    <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
      <div>
        <dt className="text-gray-500 dark:text-gray-300">Destination</dt>
        <dd className="font-medium text-gray-900 dark:text-white">{destinationName(country)}</dd>
      </div>
      <div>
        <dt className="text-gray-500 dark:text-gray-300">Currency</dt>
        <dd className="font-medium text-gray-900 dark:text-white">{currency}</dd>
      </div>
      <div>
        <dt className="text-gray-500 dark:text-gray-300">Method</dt>
        <dd className="font-medium text-gray-900 dark:text-white">{payoutMethodName(method)}</dd>
      </div>
      {country === "KE" && method === "MOBILE_MONEY" && (
        <div>
          <dt className="text-gray-500 dark:text-gray-300">Provider</dt>
          <dd className="font-medium text-gray-900 dark:text-white">Safaricom</dd>
        </div>
      )}
    </dl>
  );
}

function EarningRow({
  earning,
  payment,
  payout,
}: {
  earning: Earning;
  payment: Payment | null;
  payout: Payout | null;
}) {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const inFlight = useRef(false);
  const statusQuery = useQuery({
    queryKey: ["payouts", payout?.id, "payaza-status"],
    queryFn: () => checkPayazaPayoutStatus(payout!.id),
    enabled: payout?.status === "PAYOUT_PROCESSING",
    retry: false,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => {
      const status = query.state.data?.payout?.status;
      if (status && status !== "PAYOUT_PROCESSING") return false;
      if (query.state.dataUpdateCount + query.state.fetchFailureCount >= 4) return false;
      return 20000;
    },
  });
  const refreshedPayout = statusQuery.data?.payout;
  const displayed =
    refreshedPayout && refreshedPayout.id === payout?.id ? refreshedPayout : payout;

  useEffect(() => {
    const updated = statusQuery.data?.payout;
    if (!updated) return;
    queryClient.setQueryData<Payout[]>(payoutQueryKey, (current) => replacePayout(current, updated));
  }, [queryClient, statusQuery.data]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: earningsQueryKey }),
      queryClient.invalidateQueries({ queryKey: paymentQueryKey }),
      queryClient.invalidateQueries({ queryKey: payoutQueryKey }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (eligible: Payment) => createPayout(eligible),
    onSuccess: async (created) => {
      queryClient.setQueryData<Payout[]>(payoutQueryKey, (current) => replacePayout(current, created));
      setNotice(payoutStatusLabel[created.status]);
      await refresh();
    },
    onError: (error) => setNotice(readPayoutError(error)),
  });

  const sendMutation = useMutation({
    mutationFn: (payoutId: number) => startPayazaPayout(payoutId),
    onSuccess: async (result) => {
      queryClient.setQueryData<Payout[]>(payoutQueryKey, (current) => replacePayout(current, result.payout));
      setNotice(payoutStatusLabel[result.payout.status]);
      await refresh();
    },
    onError: (error) => setNotice(readPayoutError(error)),
  });

  const checkMutation = useMutation({
    mutationFn: (payoutId: number) => checkPayazaPayoutStatus(payoutId),
    onSuccess: async (result) => {
      queryClient.setQueryData<Payout[]>(payoutQueryKey, (current) => replacePayout(current, result.payout));
      setNotice(payoutStatusLabel[result.payout.status]);
      await refresh();
    },
    onError: (error) => setNotice(readPayoutError(error)),
  });

  const earnedAt = new Date(earning.earned_at);
  const dateLabel = Number.isNaN(earnedAt.getTime()) ? earning.earned_at : earnedAt.toLocaleDateString();
  const currency = displayed?.currency ?? payment?.currency ?? null;
  const canRequest =
    payment?.status === "PAYMENT_RECEIVED" &&
    payment.currency === "KES" &&
    (!displayed || displayed.status === "PAYOUT_FAILED" || displayed.status === "PAYOUT_CANCELLED");
  const busy = createMutation.isPending || sendMutation.isPending || checkMutation.isPending;

  const run = (action: () => void) => {
    if (inFlight.current || busy) return;
    inFlight.current = true;
    setNotice(null);
    action();
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-slate-700">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{earning.job.title}</p>
          <p className="text-sm font-semibold text-slate-800 dark:text-gray-100">
            {currency ? formatPaymentAmount(earning.amount, currency) : formatSummaryAmount({ currency: null, mixedCurrency: false }, Number(earning.amount))}
          </p>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">{dateLabel}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {payment && (
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${paymentStatusClass[payment.status]}`}>
              {paymentStatusLabel[payment.status]}
            </span>
          )}
          {displayed && (
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${payoutStatusClass[displayed.status]}`}>
              {payoutStatusLabel[displayed.status]}
            </span>
          )}
        </div>
      </div>

      {canRequest && payment && (
        <div className="space-y-3">
          <PayoutDestination country="KE" currency="KES" method="MOBILE_MONEY" />
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              run(() =>
                createMutation.mutate(payment, {
                  onSettled: () => {
                    inFlight.current = false;
                  },
                }),
              )
            }
            className={actionButtonClass}
            style={{ backgroundColor: "#70e000" }}
          >
            {createMutation.isPending ? "Requesting payout..." : "Request payout"}
          </button>
        </div>
      )}

      {displayed && !canRequest && (
        <PayoutDestination
          country={displayed.destination_country}
          currency={displayed.destination_currency}
          method={displayed.payout_method}
        />
      )}

      {displayed?.status === "PAYOUT_PENDING" && (
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            run(() =>
              sendMutation.mutate(displayed.id, {
                onSettled: () => {
                  inFlight.current = false;
                },
              }),
            )
          }
          className={actionButtonClass}
          style={{ backgroundColor: "#70e000" }}
        >
          {sendMutation.isPending ? "Sending payout..." : "Send payout"}
        </button>
      )}

      {displayed?.status === "PAYOUT_PROCESSING" && (
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            run(() =>
              checkMutation.mutate(displayed.id, {
                onSettled: () => {
                  inFlight.current = false;
                },
              }),
            )
          }
          className={actionButtonClass}
          style={{ backgroundColor: "#70e000" }}
        >
          {checkMutation.isPending ? "Checking status..." : "Check status"}
        </button>
      )}

      {payment?.status === "PAYMENT_RECEIVED" && payment.currency !== "KES" && !displayed && (
        <p className="text-sm text-gray-500 dark:text-gray-300">Payout sending is available for KES payments.</p>
      )}
      {displayed?.status === "PAYOUT_PROCESSING" && (
        <p className="text-sm text-gray-500 dark:text-gray-300">
          This payout is still being processed. Status is checked a few times, then use Check status to refresh.
        </p>
      )}
      {notice && <p className="text-sm text-slate-700 dark:text-gray-200">{notice}</p>}
      {statusQuery.isError && <p className="text-sm text-red-600">{readPayoutError(statusQuery.error)}</p>}
    </div>
  );
}

const EarningsPage = () => {
  const earningsQuery = useQuery({ queryKey: earningsQueryKey, queryFn: fetchEarnings });
  const paymentsQuery = useQuery({ queryKey: paymentQueryKey, queryFn: fetchPayments });
  const payoutsQuery = useQuery({ queryKey: payoutQueryKey, queryFn: fetchPayouts });
  const summary = summarizeEarnings(
    earningsQuery.data ?? [],
    paymentsQuery.data ?? [],
    payoutsQuery.data ?? [],
  );
  const summaryCards = [
    { title: "Total Earnings", value: formatSummaryAmount(summary, summary.total) },
    { title: "Pending", value: formatSummaryAmount(summary, summary.pending) },
    { title: "Paid", value: formatSummaryAmount(summary, summary.paid) },
  ];
  const payoutStatusUnavailable = payoutsQuery.isError || paymentsQuery.isError;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Earnings</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          Project earnings and payouts for your account.
        </p>
      </section>

      {earningsQuery.isLoading ? (
        <div className="grid animate-pulse gap-6 md:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="h-24 rounded-xl bg-gray-200 dark:bg-slate-800" />
          ))}
        </div>
      ) : earningsQuery.isError ? (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <p className="text-sm text-red-600">We couldn't load your earnings. Please try again.</p>
          <button
            type="button"
            onClick={() => void earningsQuery.refetch()}
            className={`${actionButtonClass} mt-4`}
            style={{ backgroundColor: "#70e000" }}
          >
            Try again
          </button>
        </section>
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          {summaryCards.map((card) => (
            <div
              key={card.title}
              className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-slate-800"
            >
              <p className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-300">{card.title}</p>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                {card.title === "Total Earnings" || !payoutStatusUnavailable ? card.value : "Unavailable"}
              </p>
            </div>
          ))}
        </div>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h4 className="mb-4 text-base font-semibold text-slate-900 dark:text-white">Recent Payments</h4>
        {earningsQuery.isLoading ? (
          <p className="text-sm text-gray-500 dark:text-gray-300">Loading earnings...</p>
        ) : earningsQuery.isError ? (
          <p className="text-sm text-red-600">{readApiError(earningsQuery.error)}</p>
        ) : (earningsQuery.data ?? []).length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-300">No earnings yet.</p>
        ) : (
          <div className="space-y-3">
            {payoutStatusUnavailable && (
              <p className="text-sm text-red-600">We couldn't load payout status. Please try again.</p>
            )}
            {(earningsQuery.data ?? []).map((earning) => {
              const payment = paymentForEarning(earning, paymentsQuery.data ?? []);
              const payout = payment ? currentPayoutForPayment(payoutsQuery.data ?? [], payment.id) : null;
              return <EarningRow key={earning.id} earning={earning} payment={payment} payout={payout} />;
            })}
          </div>
        )}
      </section>
    </div>
  );
};

export default EarningsPage;
