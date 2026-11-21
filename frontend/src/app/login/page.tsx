"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/toast"

export default function LoginPage() {
  const [isAdmin, setIsAdmin] = useState(true)
  const [loading, setLoading] = useState(false)
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const router = useRouter()
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    const res = await signIn(isAdmin ? "admin-login" : "portal-login", {
      username: isAdmin ? identifier : undefined,
      phone_number: !isAdmin ? identifier : undefined,
      password,
      redirect: false,
    })

    setLoading(false)

    if (res?.error) {
      toast({ title: "Login Failed", description: "Invalid credentials", variant: "destructive" })
    } else {
      router.push(isAdmin ? "/dashboard" : "/portal")
    }
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">ISP Billing System</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex w-full mb-6 rounded-md border p-1">
            <button
              className={`flex-1 rounded py-1.5 text-sm font-medium transition-all ${isAdmin ? 'bg-background shadow' : 'text-muted-foreground'}`}
              onClick={() => setIsAdmin(true)}
              type="button"
            >
              Admin
            </button>
            <button
              className={`flex-1 rounded py-1.5 text-sm font-medium transition-all ${!isAdmin ? 'bg-background shadow' : 'text-muted-foreground'}`}
              onClick={() => setIsAdmin(false)}
              type="button"
            >
              Customer
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="identifier">{isAdmin ? "Username" : "Phone Number"}</Label>
              <Input
                id="identifier"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder={isAdmin ? "admin" : "0712345678"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Button className="w-full" type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
