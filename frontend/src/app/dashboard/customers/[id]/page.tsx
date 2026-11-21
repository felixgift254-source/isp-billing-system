"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Customer } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { getStatusColor, formatCurrency } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export default function CustomerDetailPage({ params }: { params: { id: string } }) {
  const { data: session } = useSession()
  const [customer, setCustomer] = useState<Customer | null>(null)

  useEffect(() => {
    if (session?.access_token) {
      api.get<Customer>(`/customers/${params.id}`, session.access_token)
         .then(setCustomer)
         .catch(console.error)
    }
  }, [session, params.id])

  if (!customer) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">{customer.full_name}</h1>
        <div className="space-x-2">
          <Button variant="outline">Change Plan</Button>
          <Button variant={customer.status === 'ACTIVE' ? 'destructive' : 'default'}>
            {customer.status === 'ACTIVE' ? 'Suspend' : 'Activate'}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Profile Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge className={getStatusColor(customer.status)}>{customer.status}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Connection</span>
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${customer.is_online ? 'bg-green-500' : 'bg-gray-300'}`} />
                {customer.is_online ? 'Online' : 'Offline'}
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Phone</span>
              <span>{customer.phone_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">PPPoE Username</span>
              <span className="font-mono bg-muted px-2 rounded">{customer.pppoe_username}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Subscription</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Plan</span>
              <span className="font-medium">{customer.plan?.name || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Balance</span>
              <span className={customer.balance < 0 ? 'text-red-500 font-bold' : ''}>
                {formatCurrency(customer.balance)}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
