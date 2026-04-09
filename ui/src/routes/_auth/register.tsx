import { zodResolver } from "@hookform/resolvers/zod";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Form } from "@/components/ui/Form";
import { TextField } from "@/components/ui/TextField";
import { api } from "@/lib/api-client";
import { setTokens } from "@/lib/auth";
import { registerSchema, type RegisterForm } from "@/lib/schemas";

export const Route = createFileRoute("/_auth/register")({
  component: RegisterPage,
});

function RegisterPage() {
  const router = useRouter();
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
      const result = await api<{ access_token: string; refresh_token: string }>("/auth/register", {
        method: "POST",
        body: data,
      });
      setTokens(result.access_token, result.refresh_token);
      router.navigate({ to: "/" });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold">Create an account</h2>
      <p className="mt-2 text-sm text-neutral-500">Enter your details to get started.</p>

      {apiError && <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{apiError}</div>}

      <Form onSubmit={handleSubmit(onSubmit)} className="mt-8">
        <Controller
          control={control}
          name="name"
          render={({ field, fieldState }) => (
            <TextField
              label="Name"
              autoComplete="name"
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
              autoComplete="new-password"
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              isInvalid={fieldState.invalid}
              errorMessage={fieldState.error?.message}
            />
          )}
        />

        <Button type="submit" isDisabled={isSubmitting} className="w-full">
          {isSubmitting ? "Creating account..." : "Create account"}
        </Button>
      </Form>

      <p className="mt-4 text-center text-sm text-neutral-500">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-neutral-900 underline">
          Login
        </Link>
      </p>
    </div>
  );
}
