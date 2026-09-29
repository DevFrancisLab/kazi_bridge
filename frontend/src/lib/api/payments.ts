import axios from "axios";
import api from "@/lib/api";

export type PaymentStatus =
  | "PAYMENT_PENDING"
  | "PAYMENT_PROCESSING"
  | "PAYMENT_RECEIVED"
  | "PAYMENT_FAILED"
  | "PAYMENT_CANCELLED";

export interface Payment {
  id: number;
  job: number;
  amount: string;
  currency: string;
  transaction_reference: string;
  provider_transaction_reference: string | null;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
}

export interface PayazaPaymentResponse {
  error: string | null;
  message?: string | null;
  initialized?: boolean;
  payaza_response_code?: string | null;
  payaza_response_message?: string | null;
  payaza_transaction_status?: string | null;
  local_status_changed?: boolean;
  payment: Payment;
}

export interface ClientJobSummary {
  id: number;
  title: string;
  budget: string | number;
  status: string;
  freelancer: {
    id: number;
    email: string;
    role: string;
  } | null;
}

export const paymentQueryKey = ["payments"] as const;

export const paymentStatusLabel: Record<PaymentStatus, string> = {
  PAYMENT_PENDING: "Payment pending",
  PAYMENT_PROCESSING: "Payment processing",
  PAYMENT_RECEIVED: "Payment received",
  PAYMENT_FAILED: "Payment failed",
  PAYMENT_CANCELLED: "Payment cancelled",
};

export const paymentStatusClass: Record<PaymentStatus, string> = {
  PAYMENT_PENDING: "bg-amber-100 text-amber-700",
  PAYMENT_PROCESSING: "bg-sky-100 text-sky-700",
  PAYMENT_RECEIVED: "bg-emerald-100 text-emerald-700",
  PAYMENT_FAILED: "bg-red-100 text-red-700",
  PAYMENT_CANCELLED: "bg-gray-100 text-gray-600",
};

const ACTIVE_STATUSES: PaymentStatus[] = [
  "PAYMENT_PENDING",
  "PAYMENT_PROCESSING",
  "PAYMENT_RECEIVED",
];

/** The only KES collection bank code the KaziBridge API accepts. */
const KES_COLLECTION_BANK_CODE = "SAFKEN";

const paymentFlow: PaymentStatus[] = [
  "PAYMENT_PENDING",
  "PAYMENT_PROCESSING",
  "PAYMENT_RECEIVED",
];

export const paymentFlowSteps = paymentFlow.map((status) => ({
  status,
  label: paymentStatusLabel[status],
}));

export function formatPaymentAmount(amount: string | number, currency: string): string {
  const numeric = typeof amount === "number" ? amount : Number(amount);
  const rendered = Number.isFinite(numeric)
    ? numeric.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : String(amount);
  return `${currency} ${rendered}`;
}

export function currentPaymentForJob(payments: Payment[], jobId: number): Payment | null {
  const rows = payments.filter((payment) => payment.job === jobId);
  return rows.find((payment) => ACTIVE_STATUSES.includes(payment.status)) ?? rows[0] ?? null;
}

export function readApiError(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error && error.message
      ? error.message
      : "Something went wrong. Please try again.";
  }
  if (!error.response) {
    return "Network error. Please check your connection.";
  }
  if (error.response.status === 401) {
    return "Please sign in again to continue this payment.";
  }
  if (error.response.status === 403) {
    return "You do not have permission to manage this payment.";
  }
  const data: unknown = error.response.data;
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message;
    }
    if (typeof record.detail === "string" && record.detail.trim()) {
      return record.detail;
    }
    const parts: string[] = [];
    for (const value of Object.values(record)) {
      if (typeof value === "string" && value.trim()) {
        parts.push(value);
      } else if (Array.isArray(value)) {
        for (const item of value) {
          if (typeof item === "string" && item.trim()) {
            parts.push(item);
          }
        }
      }
    }
    if (parts.length > 0) {
      return parts.join(" ");
    }
  }
  return "The payment could not be completed. Please try again.";
}

async function fetchAll<T>(path: string): Promise<T[]> {
  const collected: T[] = [];
  let nextUrl: string | null = path;
  for (let page = 0; page < 20 && nextUrl; page += 1) {
    const response = await api.get<unknown>(nextUrl);
    const body: unknown = response.data;
    if (Array.isArray(body)) {
      return body as T[];
    }
    if (!body || typeof body !== "object") {
      return collected;
    }
    const record = body as { results?: unknown; next?: unknown };
    if (Array.isArray(record.results)) {
      collected.push(...(record.results as T[]));
    }
    nextUrl = typeof record.next === "string" && record.next.length > 0 ? record.next : null;
  }
  return collected;
}

export function fetchPayments(): Promise<Payment[]> {
  return fetchAll<Payment>("payments/");
}

export function fetchClientJobs(): Promise<ClientJobSummary[]> {
  return fetchAll<ClientJobSummary>("jobs/");
}

export async function createPayment(jobId: number): Promise<Payment> {
  const response = await api.post<Payment>("payments/", { job: jobId });
  return response.data;
}

export async function startPayazaPayment(paymentId: number): Promise<PayazaPaymentResponse> {
  const response = await api.post<PayazaPaymentResponse>(`payments/${paymentId}/payaza/`, {
    customer_bank_code: KES_COLLECTION_BANK_CODE,
  });
  return response.data;
}

export async function checkPayazaPaymentStatus(paymentId: number): Promise<PayazaPaymentResponse> {
  const response = await api.get<PayazaPaymentResponse>(`payments/${paymentId}/payaza/status/`);
  return response.data;
}

export function replacePayment(payments: Payment[] | undefined, payment: Payment): Payment[] {
  const rows = payments ?? [];
  const rest = rows.filter((row) => row.id !== payment.id);
  return [payment, ...rest];
}

export type PayoutStatus =
  | "PAYOUT_PENDING"
  | "PAYOUT_PROCESSING"
  | "PAYOUT_PAID"
  | "PAYOUT_FAILED"
  | "PAYOUT_CANCELLED";

export type PayoutMethod = "MOBILE_MONEY" | "BANK_TRANSFER";

export interface Payout {
  id: number;
  payment: number;
  amount: string;
  currency: string;
  destination_country: string;
  destination_currency: string;
  payout_method: PayoutMethod;
  transaction_reference: string;
  provider_transaction_reference: string | null;
  status: PayoutStatus;
  created_at: string;
  updated_at: string;
}

export interface PayazaPayoutResponse {
  error: string | null;
  message?: string | null;
  initialized?: boolean;
  payaza_response_code?: string | null;
  payaza_response_status?: string | null;
  payaza_transaction_status?: string | null;
  local_status_changed?: boolean;
  payout: Payout;
}

export interface Earning {
  id: number;
  amount: string;
  earned_at: string;
  job: {
    id: number;
    title: string;
  };
  freelancer: {
    id: number;
    email: string;
    role: string;
  };
}

export const earningsQueryKey = ["earnings"] as const;
export const payoutQueryKey = ["payouts"] as const;

export const payoutStatusLabel: Record<PayoutStatus, string> = {
  PAYOUT_PENDING: "Payout pending",
  PAYOUT_PROCESSING: "Payout processing",
  PAYOUT_PAID: "Paid",
  PAYOUT_FAILED: "Payout failed",
  PAYOUT_CANCELLED: "Payout cancelled",
};

export const payoutStatusClass: Record<PayoutStatus, string> = {
  PAYOUT_PENDING: "bg-amber-100 text-amber-700",
  PAYOUT_PROCESSING: "bg-sky-100 text-sky-700",
  PAYOUT_PAID: "bg-emerald-100 text-emerald-700",
  PAYOUT_FAILED: "bg-red-100 text-red-700",
  PAYOUT_CANCELLED: "bg-gray-100 text-gray-600",
};

const ACTIVE_PAYOUT_STATUSES: PayoutStatus[] = [
  "PAYOUT_PENDING",
  "PAYOUT_PROCESSING",
  "PAYOUT_PAID",
];

export function fetchEarnings(): Promise<Earning[]> {
  return fetchAll<Earning>("earnings/");
}

export function fetchPayouts(): Promise<Payout[]> {
  return fetchAll<Payout>("payouts/");
}

export function paymentForEarning(earning: Earning, payments: Payment[]): Payment | null {
  return (
    payments.find(
      (payment) => payment.job === earning.job.id && payment.status === "PAYMENT_RECEIVED",
    ) ?? null
  );
}

export function currentPayoutForPayment(payouts: Payout[], paymentId: number): Payout | null {
  const rows = payouts.filter((payout) => payout.payment === paymentId);
  return rows.find((payout) => ACTIVE_PAYOUT_STATUSES.includes(payout.status)) ?? rows[0] ?? null;
}

export function replacePayout(payouts: Payout[] | undefined, payout: Payout): Payout[] {
  const rows = payouts ?? [];
  return [payout, ...rows.filter((row) => row.id !== payout.id)];
}

export interface EarningsSummary {
  total: number;
  pending: number;
  paid: number;
  currency: string | null;
  mixedCurrency: boolean;
}

function amountNumber(amount: string | number): number {
  const numeric = typeof amount === "number" ? amount : Number(amount);
  return Number.isFinite(numeric) ? numeric : 0;
}

export function summarizeEarnings(
  earnings: Earning[],
  payments: Payment[],
  payouts: Payout[],
): EarningsSummary {
  const currencies = new Set<string>();
  let total = 0;
  let pending = 0;
  let paid = 0;
  for (const earning of earnings) {
    const value = amountNumber(earning.amount);
    total += value;
    const payment = paymentForEarning(earning, payments);
    if (payment?.currency) currencies.add(payment.currency);
    const payout = payment ? currentPayoutForPayment(payouts, payment.id) : null;
    if (payout?.currency) currencies.add(payout.currency);
    if (payout?.status === "PAYOUT_PAID") paid += value;
    else pending += value;
  }
  return {
    total,
    pending,
    paid,
    currency: currencies.size === 1 ? [...currencies][0] : null,
    mixedCurrency: currencies.size > 1,
  };
}

export function formatSummaryAmount(
  summary: Pick<EarningsSummary, "currency" | "mixedCurrency">,
  amount: number,
): string {
  const rendered = amount.toLocaleString("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (summary.mixedCurrency) return `${rendered} (mixed currencies)`;
  if (!summary.currency) return rendered;
  return `${summary.currency} ${rendered}`;
}

export function readPayoutError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data: unknown = error.response?.data;
    if (data && typeof data === "object" && (data as { error?: unknown }).error === "missing_freelancer_information") {
      return "Complete your payout details before requesting a payout.";
    }
  }
  const message = readApiError(error);
  if (message === "Please sign in again to continue this payment.") {
    return "Please sign in again to continue.";
  }
  if (message === "You do not have permission to manage this payment.") {
    return "You do not have permission to manage this payout.";
  }
  return message;
}

export async function createPayout(payment: Payment): Promise<Payout> {
  const response = await api.post<Payout>("payouts/", {
    payment: payment.id,
    destination_country: "KE",
    destination_currency: payment.currency,
    payout_method: "MOBILE_MONEY",
  });
  return response.data;
}

export async function startPayazaPayout(payoutId: number): Promise<PayazaPayoutResponse> {
  const response = await api.post<PayazaPayoutResponse>(`payouts/${payoutId}/payaza/`, {});
  return response.data;
}

export async function checkPayazaPayoutStatus(payoutId: number): Promise<PayazaPayoutResponse> {
  const response = await api.get<PayazaPayoutResponse>(`payouts/${payoutId}/payaza/status/`);
  return response.data;
}
