import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { redirect } from "next/navigation"
import { LogOut } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions)
  
  if (!session || session.role !== "customer") {
    redirect("/login")
  }

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-bold">ISP Portal</span>
            <nav className="flex gap-4">
              <Link href="/portal" className="text-sm font-medium hover:text-primary">Overview</Link>
              <Link href="/portal/payments" className="text-sm font-medium hover:text-primary">Payments</Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{session.user?.name}</span>
            <Link href="/api/auth/signout">
              <Button variant="ghost" size="icon">
                <LogOut className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>
      <main className="container py-6">
        {children}
      </main>
    </div>
  )
}
