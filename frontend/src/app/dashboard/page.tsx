"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { DashboardMetrics } from "@/types"
import { StatsCard } from "@/components/dashboard/stats-card"
import { MetricChart } from "@/components/dashboard/metric-chart"
import { PaymentHistory } from "@/components/payments/payment-history"
import { Users, CreditCard, FileText, Activity } from "lucide-react"

export default function DashboardHome() {
  const { data: session } = useSession()
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      if (session?.access_token) {
        try {
          const data = await api.get<DashboardMetrics>("/dashboard/metrics", session.access_token)
          setMetrics(data)
        } catch (error) {
          console.error("Failed to fetch metrics", error)
        }
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [session])

  if (!metrics) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard title="Active Customers" value={metrics.active_customers} icon={Users} />
        <StatsCard title="Monthly Revenue" value={`KES ${metrics.monthly_revenue}`} icon={CreditCard} />
        <StatsCard title="Pending Invoices" value={metrics.pending_invoices} icon={FileText} />
        <StatsCard title="Routers Online" value={metrics.routers.filter(r => r.status === 'ONLINE').length} icon={Activity} />
      </div>

      <div className="grid gap-4 grid-cols-1 lg:grid-cols-7">
        <div className="col-span-1 lg:col-span-4">
          <MetricChart />
        </div>
        <div className="col-span-1 lg:col-span-3 rounded-xl border bg-card text-card-foreground shadow space-y-4 p-6">
           <h3 className="font-semibold leading-none tracking-tight">Recent Payments</h3>
           <PaymentHistory payments={metrics.recent_payments} />
        </div>
      </div>
    </div>
  )
}
