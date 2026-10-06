import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { DownloadIcon, KeyRoundIcon, LogOutIcon, Trash2Icon, UserIcon } from "lucide-react";
import { FormTextField } from "@/components/FormTextField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { accountApi } from "@/lib/account-api";
import { saveBlob } from "@/lib/api-client";
import { clearAccessToken } from "@/lib/auth";
import { CURRENCIES, DEFAULT_CURRENCY, DEFAULT_LOCALE, LOCALES, setDisplayLocale } from "@/lib/currency";
import { changePasswordSchema, type ChangePasswordForm } from "@/lib/schemas";
import type { Profile, User } from "@/lib/types";

export function SettingsPage() {
  const me = useQuery({ queryKey: ["me"], queryFn: accountApi.getMe });
  const profile = useQuery({ queryKey: ["profile"], queryFn: accountApi.getProfile });

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-xs text-muted-foreground">Manage your profile, security, and data.</p>
      </div>

      {me.data && profile.isSuccess ? (
        <ProfileCard user={me.data} profile={profile.data} />
      ) : (
        <Skeleton className="h-64 w-full" />
      )}
      <SecurityCard />
      <DataCard />
    </div>
  );
}

function ProfileCard({ user, profile }: { user: User; profile: Profile | null }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(user.name);
  const [currency, setCurrency] = useState(profile?.currency ?? DEFAULT_CURRENCY);
  const [locale, setLocale] = useState(profile?.locale ?? DEFAULT_LOCALE);

  const save = useMutation({
    mutationFn: async () => {
      const trimmed = name.trim();
      if (!trimmed) throw new Error("Name is required");
      const [updatedUser, updatedProfile] = await Promise.all([
        trimmed === user.name ? Promise.resolve(user) : accountApi.updateMe(trimmed),
        accountApi.updateProfile({
          display_name: profile?.display_name ?? null,
          phone: profile?.phone ?? null,
          timezone: profile?.timezone ?? null,
          currency,
          locale,
        }),
      ]);
      return { updatedUser, updatedProfile };
    },
    onSuccess: ({ updatedUser, updatedProfile }) => {
      setDisplayLocale(updatedProfile.locale);
      queryClient.setQueryData(["me"], updatedUser);
      queryClient.setQueryData(["profile"], updatedProfile);
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserIcon className="size-4 text-primary" /> Profile
        </CardTitle>
        <CardDescription>{user.email}</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          <FieldGroup>
            {save.isError ? (
              <Alert variant="destructive">
                <AlertDescription>{save.error.message}</AlertDescription>
              </Alert>
            ) : null}
            <Field>
              <FieldLabel htmlFor="settings-name">Name</FieldLabel>
              <Input id="settings-name" value={name} onChange={(event) => setName(event.target.value)} />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="settings-currency">Default currency</FieldLabel>
                <Select value={currency} onValueChange={(value) => value && setCurrency(value)}>
                  <SelectTrigger id="settings-currency" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {CURRENCIES.map((option) => (
                        <SelectItem key={option.code} value={option.code}>
                          {option.code} · {option.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <FieldDescription>Used for new plans. Existing plans keep their currency.</FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="settings-locale">Number &amp; date format</FieldLabel>
                <Select value={locale} onValueChange={(value) => value && setLocale(value)}>
                  <SelectTrigger id="settings-locale" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {LOCALES.map((option) => (
                        <SelectItem key={option.code} value={option.code}>
                          {option.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Saving..." : "Save profile"}
              </Button>
              {save.isSuccess ? <span className="text-xs text-muted-foreground">Saved.</span> : null}
            </div>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  );
}

function SecurityCard() {
  const {
    control,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current: "", password: "", confirm: "" },
  });
  const [passwordStatus, setPasswordStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const revoke = useMutation({ mutationFn: accountApi.revokeOtherSessions });

  async function onSubmit(data: ChangePasswordForm) {
    setPasswordStatus(null);
    try {
      await accountApi.changePassword(data.current, data.password);
      reset();
      setPasswordStatus({ ok: true, message: "Password changed. Other devices have been signed out." });
    } catch (err) {
      setPasswordStatus({ ok: false, message: err instanceof Error ? err.message : "Could not change password" });
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRoundIcon className="size-4 text-primary" /> Security
        </CardTitle>
        <CardDescription>Changing your password signs you out everywhere except this browser.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <form onSubmit={handleSubmit(onSubmit)}>
          <FieldGroup>
            {passwordStatus ? (
              <Alert variant={passwordStatus.ok ? "info" : "destructive"}>
                <AlertDescription>{passwordStatus.message}</AlertDescription>
              </Alert>
            ) : null}
            <FormTextField
              control={control}
              name="current"
              label="Current password"
              type="password"
              autoComplete="current-password"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <FormTextField
                control={control}
                name="password"
                label="New password"
                type="password"
                autoComplete="new-password"
              />
              <FormTextField
                control={control}
                name="confirm"
                label="Confirm new password"
                type="password"
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" disabled={isSubmitting} className="w-fit">
              {isSubmitting ? "Changing..." : "Change password"}
            </Button>
          </FieldGroup>
        </form>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <div>
            <p className="text-sm font-medium">Sign out other devices</p>
            <p className="text-xs text-muted-foreground">
              {revoke.isSuccess
                ? "Done. Only this browser is still signed in."
                : revoke.isError
                  ? revoke.error.message
                  : "Ends every session except the one you are using now."}
            </p>
          </div>
          <Button variant="outline" onClick={() => revoke.mutate()} disabled={revoke.isPending}>
            <LogOutIcon data-icon="inline-start" />
            {revoke.isPending ? "Signing out..." : "Sign out others"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function downloadJson(data: unknown, filename: string) {
  saveBlob(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }), filename);
}

function DataCard() {
  const exportData = useMutation({
    mutationFn: accountApi.exportData,
    onSuccess: (data) => downloadJson(data, `amortsched-export-${new Date().toISOString().slice(0, 10)}.json`),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DownloadIcon className="size-4 text-primary" /> Your data
        </CardTitle>
        <CardDescription>Download everything we store about you, or delete your account.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium">Export data</p>
            <p className="text-xs text-muted-foreground">
              {exportData.isError ? exportData.error.message : "Your account, profile, and every plan as JSON."}
            </p>
          </div>
          <Button variant="outline" onClick={() => exportData.mutate()} disabled={exportData.isPending}>
            <DownloadIcon data-icon="inline-start" />
            {exportData.isPending ? "Preparing..." : "Download JSON"}
          </Button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <div>
            <p className="text-sm font-medium text-destructive">Delete account</p>
            <p className="text-xs text-muted-foreground">Permanently removes your account and all plans.</p>
          </div>
          <DeleteAccountDialog />
        </div>
      </CardContent>
    </Card>
  );
}

function DeleteAccountDialog() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const remove = useMutation({
    mutationFn: () => accountApi.deleteAccount(password),
    onSuccess: () => {
      clearAccessToken();
      queryClient.clear();
      router.navigate({ to: "/register" });
    },
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setPassword("");
          remove.reset();
        }
      }}
    >
      <DialogTrigger
        render={
          <Button variant="destructive">
            <Trash2Icon data-icon="inline-start" />
            Delete account
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete your account?</DialogTitle>
          <DialogDescription>
            This permanently deletes your account, profile, and every plan. It cannot be undone. Download an export
            first if you want to keep your data.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            remove.mutate();
          }}
          className="flex flex-col gap-4"
        >
          {remove.isError ? (
            <Alert variant="destructive">
              <AlertDescription>{remove.error.message}</AlertDescription>
            </Alert>
          ) : null}
          <Field>
            <FieldLabel htmlFor="delete-password">Confirm with your password</FieldLabel>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={!password || remove.isPending}>
              {remove.isPending ? "Deleting..." : "Delete permanently"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
