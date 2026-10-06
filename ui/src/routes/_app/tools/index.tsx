import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRightIcon, HomeIcon, PiggyBankIcon, RefreshCwIcon, ScaleIcon } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/_app/tools/")({
  component: ToolsHub,
});

const TOOLS = [
  {
    to: "/tools/affordability",
    icon: HomeIcon,
    title: "How much home can I afford?",
    description: "From your income and debts, the price, loan, and monthly payment lenders are likely to approve.",
  },
  {
    to: "/tools/refinance",
    icon: RefreshCwIcon,
    title: "Should I refinance?",
    description: "When a new rate pays back its closing costs, and what you save over the life of the loan.",
  },
  {
    to: "/tools/prepay-vs-invest",
    icon: PiggyBankIcon,
    title: "Prepay or invest?",
    description: "Whether extra cash does more paying down the loan or invested at an expected return.",
  },
  {
    to: "/",
    icon: ScaleIcon,
    title: "Which offer is cheapest?",
    description: "Select two to four plans to compare monthly cost, total cost, and the cost if you leave early.",
  },
] as const;

function ToolsHub() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Decision tools</h1>
        <p className="mt-1 text-sm text-muted-foreground">Answers to the big questions before you sign.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <Link key={tool.to} to={tool.to} className="group">
            <Card className="h-full transition-shadow group-hover:shadow-xs">
              <CardHeader>
                <tool.icon className="mb-2 size-5 text-primary" />
                <CardTitle className="flex items-center justify-between gap-2">
                  {tool.title}
                  <ArrowRightIcon className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                </CardTitle>
                <CardDescription>{tool.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
