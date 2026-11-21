"use client"

import { useEffect, useState, useCallback } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Payment } from "@/types"
import { PaymentHistory } from "@/components/payments/payment-history"
import { ReconcileDialog } from "@/components/payments/reconcile-dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatCurrency, formatDateTime } from "@/lib/utils"
import { AlertTriangle, CheckCircle2 } from "lucide-react"

export default function PaymentsPage() {
  const { data: session } = useSession()
  const [payments, setPayments] = useState<Payment[]>([])
  const [unmatched, setUnmatched] = useState<Payment[]>([])
  const [activeTab, setActiveTab] = useState<"all" | "unmatched">("all")

  const loadData = useCallback(() => {
    if (session?.access_token) {
      api.get<Payment[]>("/payments", session.access_token)
         .then(setPayments)
         .catch(console.error)

      api.get<Payment[]>("/payments/unmatched", session.access_token)
         .then(setUnmatched)
         .catch(console.error)
    }
  }, [session])

  useEffect(() => {
    loadData()
  }, [loadData])

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Payments</h1>
          <p className="text-sm text-muted-foreground">M-Pesa transaction records and customer reconciliations</p>
        </div>

        <div className="flex bg-muted p-1 rounded-lg">
          <Button
            variant={activeTab === "all" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("all")}
          >
            All Payments ({payments.length})
          </Button>
          <Button
            variant={activeTab === "unmatched" ? "default" : "ghost"}
            size="sm"
            className="gap-2"
            onClick={() => setActiveTab("unmatched")}
          >
            {unmatched.length > 0 && <AlertTriangle className="h-4 w-4 text-amber-500" />}
            Unmatched Queue ({unmatched.length})
          </Button>
        </div>
      </div>

      {activeTab === "all" ? (
        <PaymentHistory payments={payments} />
      ) : (
        <div className="rounded-md border bg-card">
          <div className="p-4 border-b">
            <h2 className="text-base font-semibold">Unassigned M-Pesa Payments</h2>
            <p className="text-xs text-muted-foreground">
              Payments where the customer entered an incorrect phone number or username in the Paybill account prompt.
            </p>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Receipt</TableHead>
                <TableHead>Sender Phone</TableHead>
                <TableHead>Entered Ref</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {unmatched.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{formatDateTime(item.transaction_date)}</TableCell>
                  <TableCell className="font-mono">{item.mpesa_receipt_number}</TableCell>
                  <TableCell>{item.phone_number}</TableCell>
                  <TableCell className="font-mono text-xs">{item.bill_ref_number || "None"}</TableCell>
                  <TableCell className="font-semibold">{formatCurrency(item.amount)}</TableCell>
                  <TableCell>
                    <ReconcileDialog
                      paymentId={item.id}
                      receiptNumber={item.mpesa_receipt_number}
                      amount={item.amount}
                      billRef={item.bill_ref_number}
                      onSuccess={loadData}
                    />
                  </TableCell>
                </TableRow>
              ))}
              {unmatched.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                    <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2 opacity-80" />
                    No unmatched payments! All transactions are reconciled.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

