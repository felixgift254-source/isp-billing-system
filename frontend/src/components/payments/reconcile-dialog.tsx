"use client"

import { useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Customer } from "@/types"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/ui/toast"
import { UserCheck, Search } from "lucide-react"

interface ReconcileDialogProps {
  paymentId: string
  receiptNumber: string
  amount: number
  billRef: string | null
  onSuccess: () => void
}

export function ReconcileDialog({
  paymentId,
  receiptNumber,
  amount,
  billRef,
  onSuccess
}: ReconcileDialogProps) {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleSearch = async () => {
    if (!session?.access_token || !search.trim()) return
    setLoading(true)
    try {
      const results = await api.get<Customer[]>(`/customers?search=${encodeURIComponent(search.trim())}`, session.access_token)
      setCustomers(results)
    } catch (err) {
      toast({
        title: "Search failed",
        description: "Could not fetch customers list",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleReconcile = async () => {
    if (!selectedCustomerId || !session?.access_token) return
    setSubmitting(true)
    try {
      await api.post(
        `/payments/${paymentId}/reconcile`,
        { customer_id: selectedCustomerId },
        session.access_token
      )
      toast({
        title: "Reconciliation complete",
        description: `Payment ${receiptNumber} successfully reconciled to customer.`
      })
      setOpen(false)
      onSuccess()
    } catch (err: any) {
      toast({
        title: "Reconciliation failed",
        description: err.message || "Failed to reconcile payment",
        variant: "destructive"
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-1.5 h-8">
          <UserCheck className="h-3.5 w-3.5 text-primary" />
          Assign
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Reconcile Payment: {receiptNumber}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-lg bg-muted p-3 text-xs space-y-1">
            <p><span className="font-semibold">Amount:</span> KES {amount}</p>
            <p><span className="font-semibold">M-Pesa Ref/Account Input:</span> {billRef || "None"}</p>
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Search customer by name, phone, or PPPoE user..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button type="button" onClick={handleSearch} disabled={loading} size="icon">
              <Search className="h-4 w-4" />
            </Button>
          </div>

          <div className="max-h-48 overflow-y-auto space-y-1 border rounded-md p-1">
            {customers.map((c) => (
              <div
                key={c.id}
                onClick={() => setSelectedCustomerId(c.id)}
                className={`p-2.5 rounded-md cursor-pointer text-sm flex justify-between items-center transition-colors ${
                  selectedCustomerId === c.id
                    ? "bg-primary text-primary-foreground font-medium"
                    : "hover:bg-muted"
                }`}
              >
                <div>
                  <p>{c.full_name}</p>
                  <p className="text-xs opacity-75">{c.phone_number} • {c.pppoe_username}</p>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full border">
                  {c.status}
                </span>
              </div>
            ))}
            {customers.length === 0 && !loading && (
              <p className="text-center text-xs text-muted-foreground py-4">
                Search customer to link this payment
              </p>
            )}
            {loading && (
              <p className="text-center text-xs text-muted-foreground py-4">Searching...</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              onClick={handleReconcile}
              disabled={!selectedCustomerId || submitting}
            >
              {submitting ? "Reconciling..." : "Confirm & Reconcile"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
