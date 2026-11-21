"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { api } from "@/lib/api"
import { Router } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function RoutersPage() {
  const { data: session } = useSession()
  const [routers, setRouters] = useState<Router[]>([])

  useEffect(() => {
    if (session?.access_token) {
      api.get<Router[]>("/routers", session.access_token)
         .then(setRouters)
         .catch(console.error)
    }
  }, [session])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Routers</h1>
        <Button>Add Router</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {routers.map((router) => (
          <Card key={router.id}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-lg">{router.name}</CardTitle>
              <div className={`h-3 w-3 rounded-full ${router.status === 'ONLINE' ? 'bg-green-500' : 'bg-red-500'}`} />
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground mb-4">{router.ip_address}</div>
              <Button variant="outline" className="w-full">Sync Profiles</Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
