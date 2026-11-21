"use client"

import { useState } from "react"
import { useSession } from "next-auth/react"
import { Payment } from "@/types"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatCurrency, formatDateTime, getStatusColor } from "@/lib/utils"
import { Download } from "lucide-react"

export function PaymentHistory({ payments }: { payments: Payment[] }) {
  const { data: session } = useSession()
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const handleDownloadReceipt = async (paymentId: string, receiptNo?: string) => {
    try {
      setDownloadingId(paymentId)
      const token = session?.access_token
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
      const response = await fetch(`${baseUrl}/payments/${paymentId}/receipt/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) {
        throw new Error("Failed to download receipt PDF")
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `receipt-${receiptNo || paymentId}.pdf`
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

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Receipt No.</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Method</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Receipt</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {payments.map((payment) => (
            <TableRow key={payment.id}>
              <TableCell>{formatDateTime(payment.transaction_date)}</TableCell>
              <TableCell className="font-mono">{payment.mpesa_receipt_number || 'N/A'}</TableCell>
              <TableCell>{payment.phone_number}</TableCell>
              <TableCell>{formatCurrency(payment.amount)}</TableCell>
              <TableCell>{payment.payment_method}</TableCell>
              <TableCell>
                <div className="flex flex-col gap-1 items-start">
                  <Badge className={getStatusColor(payment.status)}>{payment.status}</Badge>
                  {payment.reconciliation_status === "MANUALLY_ASSIGNED" && (
                    <span className="text-[10px] text-muted-foreground">Manually Reconciled</span>
                  )}
                  {payment.reconciliation_status === "PENDING_REVIEW" && (
                    <span className="text-[10px] text-amber-500 font-medium">Needs Matching</span>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  onClick={() => handleDownloadReceipt(payment.id, payment.mpesa_receipt_number)}
                  disabled={downloadingId === payment.id}
                >
                  <Download className="h-3.5 w-3.5" />
                  PDF
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {payments.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center py-6 text-muted-foreground">No payments found</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
