"use client"

import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Topbar() {
  return (
    <header className="flex h-16 items-center border-b bg-card px-6 md:hidden">
      <Button variant="ghost" size="icon" className="mr-2">
        <Menu className="h-5 w-5" />
      </Button>
      <h2 className="text-lg font-bold">ISP Admin</h2>
    </header>
  )
}
