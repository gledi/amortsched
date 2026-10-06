import { useMutation } from "@tanstack/react-query";
import { MailIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { accountApi } from "@/lib/account-api";
import type { User } from "@/lib/types";

export function VerifyEmailBanner({ user }: { user: User }) {
  const resend = useMutation({ mutationFn: accountApi.resendVerification });

  if (user.email_verified) return null;

  return (
    <Alert variant="info" className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-start gap-2.5">
        <MailIcon className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <AlertTitle>Confirm your email address</AlertTitle>
          <AlertDescription>
            {resend.isSuccess
              ? `We sent a new link to ${user.email}.`
              : resend.isError
                ? resend.error.message
                : `We sent a confirmation link to ${user.email}. It keeps your account recoverable.`}
          </AlertDescription>
        </div>
      </div>
      <Button
        size="sm"
        variant="outline"
        onClick={() => resend.mutate()}
        disabled={resend.isPending || resend.isSuccess}
      >
        {resend.isPending ? "Sending…" : resend.isSuccess ? "Sent" : "Resend email"}
      </Button>
    </Alert>
  );
}
