import { zodResolver } from "@hookform/resolvers/zod";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Form } from "@/components/ui/Form";
import { TextField } from "@/components/ui/TextField";
import { api } from "@/lib/api-client";
import { setTokens } from "@/lib/auth";
import { loginSchema, type LoginForm } from "@/lib/schemas";

export const Route = createFileRoute("/_auth/login")({
  component: LoginPage,
});

function LoginPage() {
  const router = useRouter();
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
      const params = new URLSearchParams();
      params.set("username", data.email);
      params.set("password", data.password);
      const result = await api<{ access_token: string; refresh_token: string }>("/auth/token", {
        method: "POST",
        formData: params,
      });
      setTokens(result.access_token, result.refresh_token);
      router.navigate({ to: "/" });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Welcome back</h2>
      <p className="mt-2 text-sm text-neutral-500">Enter your credentials to access your account.</p>

      {apiError && <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{apiError}</div>}

      <Form onSubmit={handleSubmit(onSubmit)} className="mt-8">
        <Controller
          control={control}
          name="email"
          render={({ field, fieldState }) => (
            <TextField
              label="Email"
              type="email"
              autoComplete="email"
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              isInvalid={fieldState.invalid}
              errorMessage={fieldState.error?.message}
            />
          )}
        />

        <Controller
          control={control}
          name="password"
          render={({ field, fieldState }) => (
            <TextField
              label="Password"
              type="password"
              autoComplete="current-password"
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              isInvalid={fieldState.invalid}
              errorMessage={fieldState.error?.message}
            />
          )}
        />

        <Button type="submit" isDisabled={isSubmitting} className="w-full">
          {isSubmitting ? "Signing in..." : "Sign in"}
        </Button>
      </Form>

      <p className="mt-4 text-center text-sm text-neutral-500">
        Don&apos;t have an account?{" "}
        <Link to="/register" className="font-medium text-neutral-900 underline">
          Register
        </Link>
      </p>
    </div>
  );
}
