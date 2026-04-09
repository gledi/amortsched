import { createFileRoute, Link, Outlet, useRouter } from "@tanstack/react-router";
import { Button } from "@/components/ui/Button";
import { Link as AriaLink } from "@/components/ui/Link";
import { clearTokens, getAccessToken, getRefreshToken } from "@/lib/auth";

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
          <p className="text-neutral-500">You need to log in to access this page.</p>
          <AriaLink href="/login" className="mt-4 inline-block">
            Go to Login
          </AriaLink>
        </div>
      </div>
    );
  },
  component: AppLayout,
});

function AppLayout() {
  const router = useRouter();

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
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
        <Link to="/" className="text-lg font-semibold">
          Amortization Schedule
        </Link>
        <Button variant="quiet" onPress={handleLogout}>
          Logout
        </Button>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
