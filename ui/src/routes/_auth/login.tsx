import { zodResolver } from "@hookform/resolvers/zod";
import { createFileRoute, Link, redirect, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { FormTextField } from "@/components/FormTextField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { accountApi } from "@/lib/account-api";
import { ApiError } from "@/lib/api-client";
import { ensureSession, safeRedirectTarget } from "@/lib/auth";
import { loginSchema, type LoginForm } from "@/lib/schemas";

interface LoginSearch {
  redirect?: string;
  reset?: boolean;
}

export const Route = createFileRoute("/_auth/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
    reset: search.reset === true || search.reset === "true" ? true : undefined,
  }),
  beforeLoad: async ({ search }) => {
    if (await ensureSession()) {
      throw redirect({ href: safeRedirectTarget(search.redirect) });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const router = useRouter();
  const search = Route.useSearch();
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(data: LoginForm) {
    setApiError(null);
    try {
      await accountApi.login(data.email, data.password);
      router.history.push(safeRedirectTarget(search.redirect));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setApiError("Incorrect email or password.");
      } else {
        setApiError(err instanceof Error ? err.message : "Login failed");
      }
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Welcome back</h2>
      <p className="mt-2 text-sm text-muted-foreground">Sign in to plan and compare your loans.</p>

      {search.reset ? (
        <Alert variant="info" className="mt-4">
          <AlertDescription>Your password was reset. Sign in with your new password.</AlertDescription>
        </Alert>
      ) : null}
      {apiError ? (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      ) : null}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8">
        <FieldGroup>
          <FormTextField control={control} name="email" label="Email" type="email" autoComplete="email" />
          <FormTextField
            control={control}
            name="password"
            label="Password"
            type="password"
            autoComplete="current-password"
          />
          <div className="-mt-2 text-right text-xs">
            <Link to="/forgot-password" className="text-muted-foreground underline hover:text-foreground">
              Forgot password?
            </Link>
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Signing in..." : "Sign in"}
          </Button>
        </FieldGroup>
      </form>

      <p className="mt-4 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link to="/register" search={{ redirect: search.redirect }} className="font-medium text-foreground underline">
          Register
        </Link>
      </p>
    </div>
  );
}
