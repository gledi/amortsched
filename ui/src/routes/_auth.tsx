import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/_auth")({
  component: AuthLayout,
});

function AuthLayout() {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden bg-zinc-900 lg:flex lg:flex-col lg:justify-center lg:px-12">
        <h1 className="text-4xl font-bold text-white">Amortization Schedule</h1>
        <p className="mt-4 text-lg text-zinc-400">Plan your loan payments with precision and clarity.</p>
      </div>
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-md space-y-6">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
