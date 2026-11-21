"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Customer, Invoice } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { formatCurrency, formatDate, getStatusColor } from "@/lib/utils"
import { StkPushDialog } from "@/components/payments/stk-push-dialog"
import { Button } from "@/components/ui/button"
import { Download, FileText } from "lucide-react"

export default function PortalHome() {
  const { data: session } = useSession()
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    if (session?.access_token) {
      api.get<any>("/portal/me", session.access_token)
        .then((data) => {
          if (data?.profile) {
            setCustomer({ ...data.profile, plan: data.plan })
          } else {
            setCustomer(data)
          }
        })
        .catch(console.error)
      api.get<Invoice[]>("/portal/invoices", session.access_token).then(setInvoices).catch(console.error)
    }
  }, [session])

  const handleDownloadInvoice = async (invoiceId: string, invoiceNum: string) => {
    try {
      setDownloadingId(invoiceId)
      const token = session?.access_token
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
      const response = await fetch(`${baseUrl}/invoices/${invoiceId}/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) {
        throw new Error("Failed to download invoice PDF")
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `invoice-${invoiceNum}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      console.error(e)
    } finally {
      setDownloadingId(null)
    }
  }

  if (!customer) return <div className="p-8 text-center text-muted-foreground">Loading your account details...</div>

  const pendingInvoice = invoices.find(i => i.status === 'PENDING' || i.status === 'OVERDUE')

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome, {customer.full_name}</h1>
        <p className="text-muted-foreground text-sm mt-1">PPPoE Account: <span className="font-mono">{customer.pppoe_username}</span></p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Connection Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className={`h-4 w-4 rounded-full ${customer.is_online ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
              <span className="font-semibold text-lg">{customer.is_online ? 'Connected' : 'Disconnected'}</span>
            </div>
            <div className="mt-4">
              <Badge className={getStatusColor(customer.status)}>{customer.status}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Current Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{customer.plan?.name || 'Standard Internet'}</div>
            <div className="text-muted-foreground mt-1">
              {customer.plan?.download_speed_mbps} Mbps ↓ / {customer.plan?.upload_speed_mbps} Mbps ↑
            </div>
            <div className="mt-4 text-sm font-medium">
              Valid until: {formatDate(customer.subscription_end)}
            </div>
          </CardContent>
        </Card>

        <Card className={pendingInvoice ? "border-amber-200 bg-amber-50/40 dark:border-amber-900/50 dark:bg-amber-900/10" : ""}>
          <CardHeader>
            <CardTitle>Account Balance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${pendingInvoice ? 'text-amber-600 dark:text-amber-400' : 'text-green-600'}`}>
              {formatCurrency(Math.max(0, -customer.balance))}
            </div>
            {pendingInvoice && (
              <div className="mt-4">
                <StkPushDialog 
                  invoiceId={pendingInvoice.id} 
                  phone={customer.phone_number} 
                  amount={pendingInvoice.amount}
                  trigger={<Button className="w-full">Pay Now via M-Pesa</Button>}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          My Invoices
        </h2>
        <div className="rounded-md border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Download</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="font-mono font-medium">{inv.invoice_number}</TableCell>
                  <TableCell>{formatDate(inv.billing_period_start)} – {formatDate(inv.billing_period_end)}</TableCell>
                  <TableCell className="font-semibold">{formatCurrency(inv.amount)}</TableCell>
                  <TableCell>{formatDate(inv.due_date)}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(inv.status)}>{inv.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1.5 text-xs"
                      onClick={() => handleDownloadInvoice(inv.id, inv.invoice_number)}
                      disabled={downloadingId === inv.id}
                    >
                      <Download className="h-3.5 w-3.5" />
                      PDF
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {invoices.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                    No invoices recorded.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
