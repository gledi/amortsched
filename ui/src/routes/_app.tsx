import { createFileRoute, Link, Outlet, useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button, buttonVariants } from "@/components/ui/button";
import { clearTokens, getAccessToken, getRefreshToken } from "@/lib/auth";
import { plansApi } from "@/lib/plans-api";
import { CalculatorIcon, LogOutIcon, UserIcon } from "lucide-react";

export const Route = createFileRoute("/_app")({
  beforeLoad: () => {
    if (!getAccessToken() && !getRefreshToken()) {
      throw new Error("Not authenticated");
    }
  },
  errorComponent: () => {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">You need to log in to access this page.</p>
          <Link to="/login" className={buttonVariants({ variant: "outline", className: "mt-4" })}>
            Go to Login
          </Link>
        </div>
      </div>
    );
  },
  component: AppLayout,
});

function AppLayout() {
  const router = useRouter();

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: plansApi.getMe,
    staleTime: 60000,
  });

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    }
    clearTokens();
    router.navigate({ to: "/login" });
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-background/95 backdrop-blur-xs px-6 py-3">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 text-base font-bold tracking-tight">
            <CalculatorIcon className="size-5 text-primary" />
            Amortization Schedule
          </Link>
          <nav className="hidden sm:flex items-center gap-4 text-xs font-medium text-muted-foreground">
            <Link to="/" className="hover:text-foreground transition-colors">
              Plans
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground">
              <UserIcon className="size-3.5" />
              <span>{user.name || user.email}</span>
            </div>
          )}
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOutIcon data-icon="inline-start" />
            Logout
          </Button>
        </div>
      </header>
      <main className="flex-1 p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}
