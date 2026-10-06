import { createFileRoute, Link, Outlet, redirect, useRouter } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { VerifyEmailBanner } from "@/components/VerifyEmailBanner";
import { accountApi } from "@/lib/account-api";
import { ensureSession, logout } from "@/lib/auth";
import { setDisplayLocale } from "@/lib/currency";
import { CalculatorIcon, LogOutIcon, SettingsIcon } from "lucide-react";

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ location }) => {
    if (!(await ensureSession())) {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
  },
  component: AppLayout,
});

const navLinkClass = "hover:text-foreground transition-colors";
const activeNavLinkProps = { className: "text-foreground" };

function AppLayout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: accountApi.getMe,
    staleTime: 60000,
  });

  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: accountApi.getProfile,
    staleTime: 60000,
  });
  setDisplayLocale(profile?.locale);

  async function handleLogout() {
    await logout();
    queryClient.clear();
    router.navigate({ to: "/login" });
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-background/95 backdrop-blur-xs px-6 py-3 print:hidden">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 text-base font-bold tracking-tight">
            <CalculatorIcon className="size-5 text-primary" />
            Amortization Schedule
          </Link>
          <nav className="hidden sm:flex items-center gap-4 text-xs font-medium text-muted-foreground">
            <Link
              to="/"
              search={{ compare: undefined }}
              className={navLinkClass}
              activeProps={activeNavLinkProps}
              activeOptions={{ exact: true, includeSearch: false }}
            >
              Plans
            </Link>
            <Link to="/tools" className={navLinkClass} activeProps={activeNavLinkProps}>
              Tools
            </Link>
            <Link to="/settings" className={navLinkClass} activeProps={activeNavLinkProps}>
              Settings
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <Link
              to="/settings"
              className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <SettingsIcon className="size-3.5" />
              <span>{user.name || user.email}</span>
            </Link>
          )}
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOutIcon data-icon="inline-start" />
            Logout
          </Button>
        </div>
      </header>
      <main className="flex-1 p-6 md:p-8 print:p-0">
        {user && !user.email_verified ? (
          <div className="mx-auto mb-6 max-w-7xl print:hidden">
            <VerifyEmailBanner user={user} />
          </div>
        ) : null}
        <Outlet />
      </main>
    </div>
  );
}
