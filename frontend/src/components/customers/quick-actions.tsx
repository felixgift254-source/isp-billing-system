"use client"

import { MoreHorizontal } from "lucide-react"
import { Customer } from "@/types"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { useRouter } from "next/navigation"

export function QuickActions({ customer }: { customer: Customer }) {
  const router = useRouter()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-8 w-8 p-0">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => router.push(`/dashboard/customers/${customer.id}`)}>
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem>
          {customer.status === 'ACTIVE' ? 'Suspend' : 'Activate'}
        </DropdownMenuItem>
        <DropdownMenuItem>Send STK Push</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
