export type UserStatus = "pending" | "active" | "rejected" | "disabled";

export interface User {
  id: number;
  email: string | null;
  username: string | null;
  status: UserStatus;
  is_global_admin: boolean;
  date_joined: string;
}

export interface SetupStatus {
  setup_required: boolean;
  can_setup: boolean;
  client_is_private: boolean;
  registration_mode: "approval" | "open";
  admin_username: string;
}

export interface RegisterResult {
  pending: boolean;
  detail: string;
}

export interface Settings {
  registration_mode: "approval" | "open";
  setup_completed: boolean;
}

export interface FinanceProfile {
  id: number;
  display_name: string;
  theme: "dark" | "light";
  created_at: string;
}

export interface SystemRelease {
  version: string;
  tag: string;
  url: string;
  published_at: string | null;
  notes: string;
}

export interface BackupRestoreTest {
  last_run?: string | null;
  last_success?: string | null;
  status?: string;
  error?: string | null;
}

export interface BackupStatus {
  last_run?: string | null;
  last_success?: string | null;
  status?: string;
  offsite?: string;
  last_error?: string | null;
  restore_test?: BackupRestoreTest | null;
  error?: string | null;
}

export interface SystemInfo {
  current_version: string;
  database: "ok" | "unavailable";
  checked_at: string | null;
  latest: SystemRelease | null;
  update_available: boolean;
  error: string | null;
  backup: BackupStatus | null;
}

export type AccountType = "cash" | "checking" | "card" | "other";
export type TransactionKind = "opening" | "income" | "expense" | "transfer";
export type AutomationKind = "transfer" | "expense";
export type AutomationIntervalUnit = "day" | "week" | "month" | "year";
export type AutomationStatus = "active" | "paused" | "suspended";
export type AutomationExecutionStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "skipped"
  | "cancelled";

export interface Account {
  id: number;
  name: string;
  type: AccountType;
  type_label: string;
  initial_balance: string;
  currency: string;
  archived: boolean;
  balance: string;
  created_at: string;
  updated_at: string;
}

export interface SavingsAccount {
  id: number;
  name: string;
  backing_account: number;
  backing_account_name: string;
  balance: string;
  created_at: string;
  updated_at: string;
}

export interface Automation {
  id: number;
  kind: AutomationKind;
  kind_label: string;
  savings: number | null;
  savings_name: string | null;
  source_account: number | null;
  source_account_name: string | null;
  amount: string;
  description: string;
  interval_count: number;
  interval_unit: AutomationIntervalUnit;
  interval_unit_label: string;
  interval_label: string;
  anchor_day: number;
  advance_notice_days: number;
  next_run_on: string;
  status: AutomationStatus;
  status_label: string;
  pending_count: number;
  created_at: string;
  updated_at: string;
}

export interface AutomationExecution {
  id: number;
  automation: number | null;
  automation_ref: number;
  automation_name: string;
  kind: AutomationKind;
  description: string;
  scheduled_date: string;
  amount: string;
  source_account: number | null;
  source_account_name: string;
  savings: number | null;
  savings_name: string;
  status: AutomationExecutionStatus;
  status_label: string;
  attempts: number;
  next_retry_at: string | null;
  failure_code: string;
  failure_label: string;
  failure_message: string;
  corrected: boolean;
  transaction: number | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationOutcome {
  rules: number;
  created: number;
  executed: number;
  pending_choice: number;
  retried: number;
  alerts: number;
}

export interface FinanceNotification {
  id: number;
  kind:
    | "automation_pending"
    | "automation_skipped"
    | "automation_suspended"
    | "automation_low_balance";
  kind_label: string;
  message: string;
  automation: number | null;
  execution: number | null;
  read_at: string | null;
  is_read: boolean;
  created_at: string;
}

export interface Line {
  id: number;
  target_type: "account" | "savings";
  account: number | null;
  account_name: string | null;
  savings: number | null;
  savings_name: string | null;
  amount: string;
  role: "principal" | "technical" | "transfer_out" | "transfer_in";
}

export interface Transaction {
  id: number;
  kind: TransactionKind;
  kind_label: string;
  date: string;
  description: string;
  amount: string;
  automation: number | null;
  automation_name: string | null;
  category: TransactionCategory | null;
  tags: string[];
  lines: Line[];
  created_at: string;
  updated_at: string;
}

export interface TransactionCategory {
  id: number;
  name: string;
  is_default: boolean;
}

export interface Category {
  id: number;
  name: string;
  is_preset: boolean;
  is_default: boolean;
}

export interface Tag {
  id: number;
  name: string;
}

export type TrashType =
  | "movement"
  | "account"
  | "savings"
  | "automation"
  | "position"
  | "operation"
  | "category"
  | "tag";

export interface TrashItem {
  type: TrashType;
  id: number;
  label: string;
  deleted_at: string | null;
  deleted_by: string | null;
}

export interface CategorySuggestion {
  category: TransactionCategory;
  source: "history" | "account" | "default";
}

export interface Dashboard {
  total_balance: string;
  total_savings: string;
  total_patrimony: string;
  total_investments_cost: string;
  total_investments_value: string;
  total_investments_unrealized: string;
  positions_without_price: number;
  period_investments_realized: string;
  period_dividends: string;
  period_balance: string;
  income_total: string;
  expense_total: string;
  period: { start: string; end: string };
  accounts: Account[];
  savings: SavingsAccount[];
  recent_transactions: Transaction[];
}

export interface SeriesPoint {
  date: string;
  saldo: string;
  patrimonio: string;
}

export interface CategoryTotal {
  id: number;
  name: string;
  total: string;
}

export interface DashboardSeries {
  buckets: SeriesPoint[];
  by_category: CategoryTotal[];
}

export type InvestmentCategory =
  | "stock"
  | "etf"
  | "bond"
  | "fund"
  | "crypto"
  | "real_estate"
  | "other";
export type InvestmentOperationKind = "opening" | "buy" | "sell" | "dividend";

export interface InvestmentPosition {
  id: number;
  name: string;
  category: InvestmentCategory | "";
  category_label: string;
  identifier: string;
  current_price: string | null;
  price_updated_on: string | null;
  archived: boolean;
  quantity: string;
  average_cost: string;
  cost: string;
  current_value: string | null;
  unrealized_gain: string | null;
  realized_gain: string;
  dividends: string;
  has_price: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvestmentSummary {
  total_cost: string;
  total_value: string;
  total_unrealized: string;
  positions_without_price: number;
  realized_gain: string;
  dividends: string;
}

export interface InvestmentPositionSummary {
  quantity: string;
  average_cost: string;
  cost: string;
  current_value: string | null;
  unrealized_gain: string | null;
  realized_gain: string;
  dividends: string;
  has_price: boolean;
}

export interface InvestmentOperation {
  id: number;
  position: number;
  kind: InvestmentOperationKind;
  kind_label: string;
  date: string;
  quantity: string | null;
  unit_price: string | null;
  gross_amount: string | null;
  commission: string;
  cash_amount: string;
  description: string;
  transaction: number | null;
  account: number | null;
  account_name: string | null;
  cost_removed: string;
  realized_gain: string;
  created_at: string;
  updated_at: string;
}

export interface InvestmentPortfolio {
  investment_account: Account | null;
  summary: InvestmentSummary;
  positions: InvestmentPosition[];
}

export interface InvestmentPositionDetail {
  position: InvestmentPosition;
  summary: InvestmentPositionSummary;
  operations: InvestmentOperation[];
}

export interface InvestmentOpeningPayload {
  date: string;
  quantity: string;
  unit_price?: string;
  total_cost?: string;
  total_amount?: string;
  description?: string;
}

export interface InvestmentPositionPayload {
  name: string;
  category?: InvestmentCategory | "";
  identifier?: string;
  current_price?: string;
  opening?: InvestmentOpeningPayload;
}

export interface InvestmentPositionUpdatePayload {
  name?: string;
  category?: InvestmentCategory | "";
  identifier?: string;
  current_price?: string | null;
  archived?: boolean;
}

export interface InvestmentOperationPayload {
  kind: InvestmentOperationKind;
  date: string;
  quantity?: string;
  unit_price?: string;
  total_amount?: string;
  commission?: string;
  amount?: string;
  description?: string;
}

export interface TransactionPayload {
  kind: "income" | "expense" | "transfer";
  date: string;
  description?: string;
  amount: string;
  account?: number;
  savings?: number;
  from_account?: number;
  to_account?: number;
  from_savings?: number;
  to_savings?: number;
  confirm_coverage?: boolean;
  category_id?: number | null;
  tags?: string[];
}

export interface ImportIssue {
  code: string;
  field: string;
  message: string;
}

export interface ImportRow {
  index: number;
  row_number: number;
  date: string;
  description: string;
  category: string;
  account: string;
  amount: string;
  kind: "opening" | "income" | "expense" | null;
  errors: ImportIssue[];
  warnings: ImportIssue[];
  not_duplicate: boolean;
}

export interface ImportAccount {
  name: string;
  normalized: string;
  state: "existing" | "new" | "similar";
  similar_to: string | null;
  will_create: boolean;
  rows: number;
  balance_before?: string;
  start_date?: string;
  first_movement?: string | null;
}

export interface ImportFormat {
  delimiter: string;
  date_format: string;
  decimal_separator: string;
  ambiguous: boolean;
}

export interface ImportOverlap {
  account: string;
  movements: number;
  from: string;
  to: string;
}

export interface ImportAnalysis {
  header: string[];
  format: ImportFormat;
  rows: ImportRow[];
  accounts: ImportAccount[];
  overlaps: ImportOverlap[];
  file_errors: ImportIssue[];
  summary: {
    rows_total: number;
    rows_ok: number;
    rows_error: number;
    accounts_to_create: number;
    income_total: string;
    expense_total: string;
    openings_total: string;
    available_total: string;
    covered_by_openings: string;
    net_total: string;
    balances: { name: string; final_balance: string }[];
    can_confirm: boolean;
  };
}

export interface ImportRowInput {
  date: string;
  description: string;
  category: string;
  account: string;
  amount: string;
  not_duplicate: boolean;
}

export interface ImportResult {
  created_accounts: string[];
  created_transactions: number;
  income_total: string;
  expense_total: string;
  openings_total: string;
  available_total: string;
  covered_by_openings: string;
  net_total: string;
  accounts: { name: string; balance: string }[];
}

export interface ArchiveBalance {
  name: string;
  balance: string;
}

export interface ArchiveAnalysis {
  can_restore: boolean;
  blocked_reason: string | null;
  manifest: {
    schema: number;
    generato_il: string;
    versione_app: string;
    profilo: string;
    valuta: string;
    conto_investimenti_id: number | null;
    conto_investimenti: string;
    conteggi: {
      conti: number;
      salvadanai: number;
      movimenti: number;
      righe: number;
      posizioni: number;
      operazioni_investimenti: number;
    };
  };
  summary: {
    accounts: number;
    savings: number;
    transactions: number;
    lines: number;
    positions: number;
    investment_operations: number;
    from: string | null;
    to: string | null;
    accounts_total: string;
    savings_total: string;
    investments_cost: string;
    investments_value: string;
    patrimony_total: string;
    balances: {
      accounts: ArchiveBalance[];
      savings: ArchiveBalance[];
    };
  };
  warnings: string[];
}

export interface ArchiveRestoreResult {
  accounts: number;
  savings: number;
  transactions: number;
  lines: number;
  positions: number;
  investment_operations: number;
  accounts_total: string;
  savings_total: string;
  investments_cost: string;
  investments_value: string;
  patrimony_total: string;
  balances: {
    accounts: ArchiveBalance[];
    savings: ArchiveBalance[];
  };
}

export class ApiError extends Error {
  status: number;
  code?: string;
  data: unknown;

  constructor(status: number, message: string, data: unknown, code?: string) {
    super(message);
    this.status = status;
    this.data = data;
    this.code = code;
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function ensureCsrf(): Promise<string> {
  let token = getCookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/csrf/", { credentials: "include" });
    token = getCookie("csrftoken");
  }
  return token ?? "";
}

function firstError(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  for (const value of Object.values(data as Record<string, unknown>)) {
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    if (value && typeof value === "object") {
      const nested = firstError(value);
      if (nested) return nested;
    }
  }
  return null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const token = await ensureCsrf();
    if (token) headers.set("X-CSRFToken", token);
  }

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const record = (data ?? {}) as Record<string, unknown>;
    throw new ApiError(
      response.status,
      firstError(data) ?? "Operazione non riuscita.",
      data,
      typeof record.code === "string" ? record.code : undefined,
    );
  }

  return data as T;
}

async function download(path: string, filename: string) {
  const response = await fetch(path, { credentials: "include" });
  if (!response.ok) {
    throw new ApiError(response.status, "Download non riuscito.", null);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  csrf: () => request("/api/auth/csrf/"),

  setupStatus: () => request<SetupStatus>("/api/auth/setup-status/"),

  setup: (password: string, passwordConfirm: string) =>
    request<{ user: User; setup_completed: boolean }>("/api/auth/setup/", {
      method: "POST",
      body: JSON.stringify({ password, password_confirm: passwordConfirm }),
    }),

  login: (identifier: string, password: string) =>
    request<{ user: User }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    }),

  logout: () =>
    request<{ detail: string }>("/api/auth/logout/", { method: "POST" }),

  me: () => request<{ user: User | null }>("/api/auth/me/"),

  profile: () => request<FinanceProfile>("/api/finance/profile/"),

  updateTheme: (theme: "dark" | "light") =>
    request<FinanceProfile>("/api/finance/profile/", {
      method: "PATCH",
      body: JSON.stringify({ theme }),
    }),

  updateEmail: (email: string) =>
    request<{ user: User }>("/api/auth/me/", {
      method: "PATCH",
      body: JSON.stringify({ email }),
    }),

  register: (email: string, password: string, passwordConfirm: string) =>
    request<RegisterResult>("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        password_confirm: passwordConfirm,
      }),
    }),

  adminUsers: (status?: UserStatus) =>
    request<{ users: User[] }>(
      `/api/admin/users/${status ? `?status=${status}` : ""}`,
    ),

  adminDecision: (userId: number, decision: "approve" | "reject") =>
    request<{ user: User }>(`/api/admin/users/${userId}/${decision}/`, {
      method: "POST",
    }),

  adminSettings: () => request<Settings>("/api/admin/settings/"),

  updateSettings: (registrationMode: "approval" | "open") =>
    request<Settings>("/api/admin/settings/", {
      method: "PATCH",
      body: JSON.stringify({ registration_mode: registrationMode }),
    }),

  adminSystem: (check = false) =>
    request<SystemInfo>(`/api/admin/system/${check ? "?check=1" : ""}`),

  dashboard: (start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const query = params.toString();
    return request<Dashboard>(`/api/finance/dashboard/${query ? `?${query}` : ""}`);
  },

  dashboardSeries: (start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const query = params.toString();
    return request<DashboardSeries>(
      `/api/finance/dashboard/series/${query ? `?${query}` : ""}`,
    );
  },

  accounts: () =>
    request<{ accounts: Account[] }>("/api/finance/accounts/"),

  createAccount: (data: {
    name: string;
    type: AccountType;
    initial_balance: string;
  }) =>
    request<Account>("/api/finance/accounts/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateAccount: (
    id: number,
    data: Partial<{ name: string; type: AccountType; archived: boolean }>,
  ) =>
    request<Account>(`/api/finance/accounts/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteAccount: (id: number) =>
    request<void>(`/api/finance/accounts/${id}/`, { method: "DELETE" }),

  savings: () =>
    request<{ savings: SavingsAccount[] }>("/api/finance/savings/"),

  createSavings: (data: { name: string; backing_account: number }) =>
    request<SavingsAccount>("/api/finance/savings/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateSavings: (id: number, data: Partial<{ name: string }>) =>
    request<SavingsAccount>(`/api/finance/savings/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteSavings: (id: number) =>
    request<void>(`/api/finance/savings/${id}/`, { method: "DELETE" }),

  investments: () =>
    request<InvestmentPortfolio>("/api/finance/investments/"),

  createInvestmentPosition: (data: InvestmentPositionPayload) =>
    request<InvestmentPosition>("/api/finance/investments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  investmentPosition: (id: number) =>
    request<InvestmentPositionDetail>(`/api/finance/investments/${id}/`),

  updateInvestmentPosition: (
    id: number,
    data: InvestmentPositionUpdatePayload,
  ) =>
    request<InvestmentPosition>(`/api/finance/investments/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteInvestmentPosition: (id: number) =>
    request<void>(`/api/finance/investments/${id}/`, { method: "DELETE" }),

  setInvestmentAccount: (account: number | null) =>
    request<{ investment_account: Account | null }>(
      "/api/finance/investments/account/",
      {
        method: "PUT",
        body: JSON.stringify({ account }),
      },
    ),

  createInvestmentOperation: (
    positionId: number,
    data: InvestmentOperationPayload,
  ) =>
    request<InvestmentOperation>(
      `/api/finance/investments/${positionId}/operations/`,
      { method: "POST", body: JSON.stringify(data) },
    ),

  updateInvestmentOperation: (
    id: number,
    data: Omit<InvestmentOperationPayload, "kind">,
  ) =>
    request<InvestmentOperation>(`/api/finance/investments/operations/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteInvestmentOperation: (id: number) =>
    request<void>(`/api/finance/investments/operations/${id}/`, {
      method: "DELETE",
    }),

  exportInvestments: () =>
    download(
      "/api/finance/investments/export/",
      `spendy-investimenti-${new Date().toISOString().slice(0, 10)}.zip`,
    ),

  automations: () =>
    request<{ automations: Automation[] }>("/api/finance/automations/"),

  createAutomation: (data: {
    kind: AutomationKind;
    savings?: number | null;
    source_account: number;
    amount: string;
    description?: string;
    interval_count: number;
    interval_unit: AutomationIntervalUnit;
    advance_notice_days: number;
    next_run_on: string;
  }) =>
    request<Automation>("/api/finance/automations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateAutomation: (
    id: number,
    data: Partial<{
      savings: number | null;
      source_account: number;
      amount: string;
      description: string;
      interval_count: number;
      interval_unit: AutomationIntervalUnit;
      advance_notice_days: number;
      next_run_on: string;
      status: "active" | "paused";
    }>,
  ) =>
    request<Automation>(`/api/finance/automations/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteAutomation: (id: number) =>
    request<void>(`/api/finance/automations/${id}/`, { method: "DELETE" }),

  runAutomation: (id: number) =>
    request<{ outcome: AutomationOutcome; automation: Automation }>(
      `/api/finance/automations/${id}/run/`,
      { method: "POST" },
    ),

  runAutomations: () =>
    request<{ outcome: AutomationOutcome }>("/api/finance/automations/run/", {
      method: "POST",
    }),

  resolveAutomation: (id: number, recover: number[]) =>
    request<{ outcome: { recovered: number; skipped: number } }>(
      `/api/finance/automations/${id}/resolve/`,
      {
        method: "POST",
        body: JSON.stringify({ recover }),
      },
    ),

  automationExecutions: (params: {
    automation?: number;
    status?: AutomationExecutionStatus;
    limit?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.automation) query.set("automation", String(params.automation));
    if (params.status) query.set("status", params.status);
    if (params.limit) query.set("limit", String(params.limit));
    const suffix = query.toString();
    return request<{ executions: AutomationExecution[]; count: number }>(
      `/api/finance/automation-executions/${suffix ? `?${suffix}` : ""}`,
    );
  },

  notifications: (params: { unread?: boolean; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.unread) query.set("unread", "1");
    if (params.limit) query.set("limit", String(params.limit));
    const suffix = query.toString();
    return request<{
      notifications: FinanceNotification[];
      unread_count: number;
    }>(`/api/finance/notifications/${suffix ? `?${suffix}` : ""}`);
  },

  markNotificationsRead: (ids?: number[]) =>
    request<{ unread_count: number }>("/api/finance/notifications/read/", {
      method: "POST",
      body: JSON.stringify(ids ? { ids } : {}),
    }),

  transactions: (params: {
    account?: number;
    savings?: number;
    start?: string;
    end?: string;
    limit?: number;
    offset?: number;
    category?: number;
    tag?: string;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.account) query.set("account", String(params.account));
    if (params.savings) query.set("savings", String(params.savings));
    if (params.start) query.set("start", params.start);
    if (params.end) query.set("end", params.end);
    if (params.limit) query.set("limit", String(params.limit));
    if (params.offset) query.set("offset", String(params.offset));
    if (params.category) query.set("category", String(params.category));
    if (params.tag) query.set("tag", params.tag);
    const suffix = query.toString();
    return request<{ transactions: Transaction[]; count: number }>(
      `/api/finance/transactions/${suffix ? `?${suffix}` : ""}`,
    );
  },

  createTransaction: (data: TransactionPayload) =>
    request<Transaction>("/api/finance/transactions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateTransaction: (id: number, data: TransactionPayload) =>
    request<Transaction>(`/api/finance/transactions/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteTransaction: (id: number) =>
    request<void>(`/api/finance/transactions/${id}/`, { method: "DELETE" }),

  categories: () => request<Category[]>("/api/finance/categories/"),

  createCategory: (name: string) =>
    request<Category>("/api/finance/categories/", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  updateCategory: (id: number, name: string) =>
    request<Category>(`/api/finance/categories/${id}/`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),

  deleteCategory: (id: number) =>
    request<void>(`/api/finance/categories/${id}/`, { method: "DELETE" }),

  tags: () => request<Tag[]>("/api/finance/tags/"),

  deleteTag: (id: number) =>
    request<void>(`/api/finance/tags/${id}/`, { method: "DELETE" }),

  trash: (type?: TrashType) =>
    request<{ items: TrashItem[]; count: number }>(
      `/api/finance/trash/${type ? `?type=${type}` : ""}`,
    ),

  restoreTrash: (type: TrashType, id: number) =>
    request<TrashItem>("/api/finance/trash/restore/", {
      method: "POST",
      body: JSON.stringify({ type, id }),
    }),

  purgeTrash: (type: TrashType, id: number) =>
    request<void>("/api/finance/trash/purge/", {
      method: "POST",
      body: JSON.stringify({ type, id }),
    }),

  emptyTrash: () =>
    request<{ purged: number }>("/api/finance/trash/empty/", {
      method: "POST",
    }),

  suggestCategory: (params: { description?: string; account?: number }) => {
    const query = new URLSearchParams();
    if (params.description) query.set("description", params.description);
    if (params.account) query.set("account", String(params.account));
    const suffix = query.toString();
    return request<CategorySuggestion>(
      `/api/finance/suggest-category/${suffix ? `?${suffix}` : ""}`,
    );
  },

  downloadImportTemplate: () =>
    download(
      "/api/finance/import/template/",
      "spendy-modello-movimenti.csv",
    ),

  exportTransactions: (params: {
    account?: number;
    savings?: number;
    start?: string;
    end?: string;
    category?: number;
    tag?: string;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.account) query.set("account", String(params.account));
    if (params.savings) query.set("savings", String(params.savings));
    if (params.start) query.set("start", params.start);
    if (params.end) query.set("end", params.end);
    if (params.category) query.set("category", String(params.category));
    if (params.tag) query.set("tag", params.tag);
    const suffix = query.toString();
    const today = new Date().toISOString().slice(0, 10);
    return download(
      `/api/finance/export/${suffix ? `?${suffix}` : ""}`,
      `spendy-movimenti-${today}.csv`,
    );
  },

  exportArchive: () => {
    const today = new Date().toISOString().slice(0, 10);
    return download(
      "/api/finance/export/archive/",
      `spendy-archivio-${today}.zip`,
    );
  },

  analyzeArchive: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<ArchiveAnalysis>("/api/finance/import/archive/analyze/", {
      method: "POST",
      body,
    });
  },

  restoreArchive: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<ArchiveRestoreResult>("/api/finance/import/archive/confirm/", {
      method: "POST",
      body,
    });
  },

  analyzeImportFile: (file: File, format?: Partial<ImportFormat>) => {
    const body = new FormData();
    body.append("file", file);
    if (format?.delimiter) body.append("delimiter", format.delimiter);
    if (format?.date_format) body.append("date_format", format.date_format);
    if (format?.decimal_separator) {
      body.append("decimal_separator", format.decimal_separator);
    }
    return request<ImportAnalysis>("/api/finance/import/analyze/", {
      method: "POST",
      body,
    });
  },

  analyzeImportRows: (rows: ImportRowInput[], format?: ImportFormat | null) =>
    request<ImportAnalysis>("/api/finance/import/analyze/", {
      method: "POST",
      body: JSON.stringify({
        rows,
        date_format: format?.date_format,
        decimal_separator: format?.decimal_separator,
      }),
    }),

  confirmImport: (rows: ImportRowInput[], format?: ImportFormat | null) =>
    request<ImportResult>("/api/finance/import/confirm/", {
      method: "POST",
      body: JSON.stringify({
        rows,
        date_format: format?.date_format,
        decimal_separator: format?.decimal_separator,
      }),
    }),
};
