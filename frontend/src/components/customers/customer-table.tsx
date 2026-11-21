"use client"

import { Customer } from "@/types"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { getStatusColor } from "@/lib/utils"
import { useRouter } from "next/navigation"
import { QuickActions } from "./quick-actions"

export function CustomerTable({ customers }: { customers: Customer[] }) {
  const router = useRouter()

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Username</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead>Plan</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {customers.map((customer) => (
            <TableRow key={customer.id} className="cursor-pointer" onClick={() => router.push(`/dashboard/customers/${customer.id}`)}>
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${customer.is_online ? 'bg-green-500' : 'bg-gray-300'}`} />
                  {customer.full_name}
                </div>
              </TableCell>
              <TableCell>{customer.pppoe_username}</TableCell>
              <TableCell>{customer.phone_number}</TableCell>
              <TableCell>{customer.plan?.name || 'N/A'}</TableCell>
              <TableCell>
                <Badge className={getStatusColor(customer.status)}>{customer.status}</Badge>
              </TableCell>
              <TableCell onClick={(e) => e.stopPropagation()}>
                <QuickActions customer={customer} />
              </TableCell>
            </TableRow>
          ))}
          {customers.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">No customers found</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
