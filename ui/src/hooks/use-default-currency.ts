import { useQuery } from "@tanstack/react-query";
import { accountApi } from "@/lib/account-api";
import { DEFAULT_CURRENCY } from "@/lib/currency";

export function useDefaultCurrency(): string {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: accountApi.getProfile, staleTime: 60000 });
  return profile?.currency ?? DEFAULT_CURRENCY;
}
