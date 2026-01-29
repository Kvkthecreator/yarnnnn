import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon, TrendingUp } from "lucide-react";

interface StatCardProps {
  label: string;
  value: number | string;
  trend?: number;
  trendLabel?: string;
  icon?: LucideIcon;
}

export function StatCard({
  label,
  value,
  trend,
  trendLabel,
  icon: Icon,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-2xl font-semibold tabular-nums">{value}</p>
          </div>
          {Icon && (
            <div className="p-2 bg-muted rounded-md">
              <Icon className="w-4 h-4 text-muted-foreground" />
            </div>
          )}
        </div>
        {trend !== undefined && trend > 0 && (
          <div className="mt-2 flex items-center gap-1 text-xs text-green-600">
            <TrendingUp className="w-3 h-3" />
            <span>+{trend}</span>
            {trendLabel && <span className="text-muted-foreground">({trendLabel})</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
