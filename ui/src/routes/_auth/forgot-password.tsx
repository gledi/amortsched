import { zodResolver } from "@hookform/resolvers/zod";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { FormTextField } from "@/components/FormTextField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { accountApi } from "@/lib/account-api";
import { forgotPasswordSchema, type ForgotPasswordForm } from "@/lib/schemas";

export const Route = createFileRoute("/_auth/forgot-password")({
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(data: ForgotPasswordForm) {
    setApiError(null);
    try {
      await accountApi.requestPasswordReset(data.email);
      setSentTo(data.email);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Could not send the reset email");
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Reset your password</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Enter the email you signed up with and we&apos;ll send you a link to choose a new password.
      </p>

      {sentTo ? (
        <Alert variant="info" className="mt-6">
          <AlertDescription>
            If an account exists for <strong className="text-foreground">{sentTo}</strong>, a reset link is on its way.
            It expires in one hour.
          </AlertDescription>
        </Alert>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="mt-8">
          {apiError ? (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{apiError}</AlertDescription>
            </Alert>
          ) : null}
          <FieldGroup>
            <FormTextField control={control} name="email" label="Email" type="email" autoComplete="email" />
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? "Sending..." : "Send reset link"}
            </Button>
          </FieldGroup>
        </form>
      )}

      <p className="mt-4 text-center text-sm text-muted-foreground">
        <Link to="/login" className="font-medium text-foreground underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
