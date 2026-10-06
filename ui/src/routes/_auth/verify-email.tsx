import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { CircleCheckIcon, CircleAlertIcon } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { accountApi } from "@/lib/account-api";

export const Route = createFileRoute("/_auth/verify-email")({
  validateSearch: (search: Record<string, unknown>): { token?: string } => ({
    token: typeof search.token === "string" ? search.token : undefined,
  }),
  component: VerifyEmailPage,
});

function VerifyEmailPage() {
  const { token } = Route.useSearch();
  const queryClient = useQueryClient();
  const verify = useMutation({
    mutationFn: accountApi.verifyEmail,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  const { mutate } = verify;
  const submittedToken = useRef<string | null>(null);

  useEffect(() => {
    if (!token || submittedToken.current === token) return;
    submittedToken.current = token;
    mutate(token);
  }, [token, mutate]);

  if (!token || verify.isError) {
    return (
      <div className="flex flex-col gap-3">
        <CircleAlertIcon className="size-8 text-destructive" />
        <h2 className="text-2xl font-bold">This link didn&apos;t work</h2>
        <p className="text-sm text-muted-foreground">
          {verify.error?.message ?? "The confirmation link is missing its token."} Sign in and use <em>Resend email</em>{" "}
          to get a fresh link.
        </p>
        <Link to="/" className={buttonVariants({ className: "mt-4 w-fit" })}>
          Continue
        </Link>
      </div>
    );
  }

  if (verify.isSuccess) {
    return (
      <div className="flex flex-col gap-3">
        <CircleCheckIcon className="size-8 text-emerald-600" />
        <h2 className="text-2xl font-bold">Email confirmed</h2>
        <p className="text-sm text-muted-foreground">Thanks, {verify.data.name}. Your account is all set.</p>
        <Link to="/" className={buttonVariants({ className: "mt-4 w-fit" })}>
          Go to my plans
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground">
      <Spinner /> Confirming your email…
    </div>
  );
}
