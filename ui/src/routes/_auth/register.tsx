import { zodResolver } from "@hookform/resolvers/zod";
import { createFileRoute, Link, redirect, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { FormTextField } from "@/components/FormTextField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { accountApi } from "@/lib/account-api";
import { ensureSession, safeRedirectTarget } from "@/lib/auth";
import { registerSchema, type RegisterForm } from "@/lib/schemas";

export const Route = createFileRoute("/_auth/register")({
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  beforeLoad: async ({ search }) => {
    if (await ensureSession()) {
      throw redirect({ href: safeRedirectTarget(search.redirect) });
    }
  },
  component: RegisterPage,
});

function RegisterPage() {
  const router = useRouter();
  const search = Route.useSearch();
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { name: "", email: "", password: "" },
  });

  async function onSubmit(data: RegisterForm) {
    setApiError(null);
    try {
      await accountApi.register(data);
      router.history.push(safeRedirectTarget(search.redirect));
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Create an account</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Model mortgages and loans, compare offers, and see what every decision costs.
      </p>

      {apiError ? (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      ) : null}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8">
        <FieldGroup>
          <FormTextField control={control} name="name" label="Name" autoComplete="name" />
          <FormTextField control={control} name="email" label="Email" type="email" autoComplete="email" />
          <FormTextField
            control={control}
            name="password"
            label="Password"
            type="password"
            autoComplete="new-password"
            description="At least 8 characters."
          />
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </FieldGroup>
      </form>

      <p className="mt-4 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" search={{ redirect: search.redirect }} className="font-medium text-foreground underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
