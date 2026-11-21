"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Customer } from "@/types"
import { CustomerTable } from "@/components/customers/customer-table"
import { CustomerForm } from "@/components/customers/customer-form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search } from "lucide-react"

export default function CustomersPage() {
  const { data: session } = useSession()
  const [customers, setCustomers] = useState<Customer[]>([])

  useEffect(() => {
    if (session?.access_token) {
      api.get<Customer[]>("/customers", session.access_token)
         .then(setCustomers)
         .catch(console.error)
    }
  }, [session])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Customers</h1>
        <CustomerForm />
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input type="search" placeholder="Search customers..." className="pl-8" />
        </div>
      </div>

      <CustomerTable customers={customers} />
    </div>
  )
}
