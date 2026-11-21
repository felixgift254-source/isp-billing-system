"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function MetricChart() {
  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>Overview</CardTitle>
      </CardHeader>
      <CardContent className="pl-2">
        <div className="h-[300px] w-full flex items-end justify-between px-4 pb-4 border-b gap-2">
          {/* Placeholder for actual chart */}
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="w-full bg-primary/20 rounded-t-sm" style={{ height: `${Math.floor(Math.random() * 80 + 20)}%` }}></div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
