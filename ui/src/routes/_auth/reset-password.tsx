import { zodResolver } from "@hookform/resolvers/zod";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { FormTextField } from "@/components/FormTextField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { accountApi } from "@/lib/account-api";
import { resetPasswordSchema, type ResetPasswordForm } from "@/lib/schemas";

export const Route = createFileRoute("/_auth/reset-password")({
  validateSearch: (search: Record<string, unknown>): { token?: string } => ({
    token: typeof search.token === "string" ? search.token : undefined,
  }),
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const router = useRouter();
  const { token } = Route.useSearch();
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirm: "" },
  });

  async function onSubmit(data: ResetPasswordForm) {
    if (!token) return;
    setApiError(null);
    try {
      await accountApi.resetPassword(token, data.password);
      router.navigate({ to: "/login", search: { reset: true } });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Could not reset your password");
    }
  }

  if (!token) {
    return (
      <div>
        <h2 className="text-2xl font-bold">Reset link missing</h2>
        <p className="mt-2 text-sm text-muted-foreground">Open the link from your email, or request a new one.</p>
        <Link to="/forgot-password" className="mt-6 inline-block text-sm font-medium underline">
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Choose a new password</h2>
      <p className="mt-2 text-sm text-muted-foreground">You&apos;ll be signed out of every other device.</p>

      {apiError ? (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>
            {apiError}{" "}
            <Link to="/forgot-password" className="underline">
              Request a new link
            </Link>
          </AlertDescription>
        </Alert>
      ) : null}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8">
        <FieldGroup>
          <FormTextField
            control={control}
            name="password"
            label="New password"
            type="password"
            autoComplete="new-password"
            description="At least 8 characters."
          />
          <FormTextField
            control={control}
            name="confirm"
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
          />
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Saving..." : "Reset password"}
          </Button>
        </FieldGroup>
      </form>
    </div>
  );
}
