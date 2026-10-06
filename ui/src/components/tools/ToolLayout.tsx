import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeftIcon } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function ToolPage({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <Link to="/tools" className="flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeftIcon className="size-3" />
          Tools
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">{children}</div>
    </div>
  );
}

export function ResultStat({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "good" | "bad";
}) {
  return (
    <Card size="sm">
      <CardHeader className="pb-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle
          className={cn(
            "text-base font-bold tabular-nums",
            tone === "good" && "text-emerald-700 dark:text-emerald-400",
            tone === "bad" && "text-destructive",
          )}
        >
          {value}
        </CardTitle>
        {detail ? <p className="text-[11px] text-muted-foreground">{detail}</p> : null}
      </CardHeader>
    </Card>
  );
}
