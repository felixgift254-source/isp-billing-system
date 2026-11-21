"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useToast } from "@/components/ui/toast"
import { api } from "@/lib/api"
import { useSession } from "next-auth/react"

export function StkPushDialog({ invoiceId, phone, amount, trigger }: { invoiceId?: string, phone: string, amount: number, trigger: React.ReactNode }) {
  const [loading, setLoading] = useState(false)
  const [phoneNumber, setPhoneNumber] = useState(phone)
  const { data: session } = useSession()
  const { toast } = useToast()

  const handlePush = async () => {
    setLoading(true)
    try {
      await api.post("/billing/stk-push", {
        phone_number: phoneNumber,
        amount,
        invoice_id: invoiceId
      }, session?.access_token as string)
      
      toast({
        title: "Success",
        description: "STK Push sent successfully to " + phoneNumber,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send STK push",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send M-Pesa Payment Request</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="phone">M-Pesa Phone Number</Label>
            <Input id="phone" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="amount">Amount (KES)</Label>
            <Input id="amount" value={amount} readOnly disabled />
          </div>
          <Button onClick={handlePush} disabled={loading} className="mt-2">
            {loading ? "Sending..." : "Send Request"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
