"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Plan } from "@/types"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { formatCurrency } from "@/lib/utils"

export default function PlansPage() {
  const { data: session } = useSession()
  const [plans, setPlans] = useState<Plan[]>([])

  useEffect(() => {
    if (session?.access_token) {
      api.get<Plan[]>("/plans", session.access_token)
         .then(setPlans)
         .catch(console.error)
    }
  }, [session])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Billing Plans</h1>
        <Button>Add Plan</Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Profile</TableHead>
              <TableHead>Speed (DL/UL)</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {plans.map((plan) => (
              <TableRow key={plan.id}>
                <TableCell className="font-medium">{plan.name}</TableCell>
                <TableCell>{plan.mikrotik_profile_name}</TableCell>
                <TableCell>{plan.download_speed_mbps} / {plan.upload_speed_mbps} Mbps</TableCell>
                <TableCell>{formatCurrency(plan.price)}</TableCell>
                <TableCell>{plan.is_active ? 'Active' : 'Inactive'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
