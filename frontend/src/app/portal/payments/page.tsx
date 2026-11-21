"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Payment } from "@/types"
import { PaymentHistory } from "@/components/payments/payment-history"

export default function PortalPayments() {
  const { data: session } = useSession()
  const [payments, setPayments] = useState<Payment[]>([])

  useEffect(() => {
    if (session?.access_token) {
      api.get<Payment[]>("/portal/payments", session.access_token)
         .then(setPayments)
         .catch(console.error)
    }
  }, [session])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Payment History</h1>
      <PaymentHistory payments={payments} />
    </div>
  )
}
