import type { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { getAccessToken, getRefreshToken, silentRefresh } from "@/lib/auth";

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: async () => {
    if (!getAccessToken() && getRefreshToken()) {
      await silentRefresh();
    }
  },
  component: RootLayout,
});

function RootLayout() {
  return <Outlet />;
}
