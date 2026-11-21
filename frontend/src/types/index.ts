export interface Router {
  id: string;
  name: string;
  ip_address: string;
  api_port: number;
  use_ssl: boolean;
  is_active: boolean;
  status: 'ONLINE' | 'OFFLINE' | 'UNREACHABLE';
  last_sync_at: string | null;
}

export interface Plan {
  id: string;
  name: string;
  mikrotik_profile_name: string;
  download_speed_mbps: number;
  upload_speed_mbps: number;
  price: number;
  validity_days: number;
  grace_period_days: number;
  is_active: boolean;
}

export interface Customer {
  id: string;
  full_name: string;
  phone_number: string;
  email: string | null;
  pppoe_username: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'EXPIRED' | 'DISABLED';
  balance: number;
  router_id: string;
  plan_id: string;
  is_online: boolean;
  last_online_at: string | null;
  billing_day: number;
  subscription_start: string;
  subscription_end: string;
  grace_period_end: string | null;
  plan?: Plan;
  router?: Router;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  customer_id: string;
  amount: number;
  due_date: string;
  status: 'PENDING' | 'PAID' | 'OVERDUE' | 'CANCELLED';
  paid_at: string | null;
  billing_period_start: string;
  billing_period_end: string;
  customer?: { full_name: string };
}

export interface Payment {
  id: string;
  mpesa_receipt_number: string;
  phone_number: string;
  amount: number;
  transaction_date: string;
  invoice_id: string | null;
  customer_id: string | null;
  payment_method: 'STK_PUSH' | 'C2B_PAYBILL';
  status: 'PENDING' | 'COMPLETED' | 'FAILED';
  reconciliation_status: 'MATCHED' | 'PENDING_REVIEW' | 'MANUALLY_ASSIGNED';
  bill_ref_number: string | null;
  matched_at: string | null;
  customer?: { full_name: string };
}

export interface DashboardMetrics {
  total_customers: number;
  active_customers: number;
  suspended_customers: number;
  monthly_revenue: number;
  pending_invoices: number;
  overdue_invoices: number;
  routers: {
    name: string;
    status: string;
    connected_users: number;
  }[];
  recent_payments: Payment[];
}
