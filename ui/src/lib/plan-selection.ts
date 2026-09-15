const MAX_SELECTED_PLANS = 4;
const MIN_SELECTED_PLANS = 2;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function isPlanId(id: string): boolean {
  return uuidPattern.test(id);
}

export function parsePlanIds(value: unknown): string[] {
  if (typeof value !== "string") {
    return [];
  }

  return [
    ...new Set(
      value
        .split(",")
        .map((id) => id.trim().toLowerCase())
        .filter(Boolean),
    ),
  ];
}

export function isComparableSelection(ids: readonly string[]): boolean {
  return ids.length >= MIN_SELECTED_PLANS && ids.length <= MAX_SELECTED_PLANS;
}

export function restorePlanSelection(value: unknown, availableIds: readonly string[]) {
  const requested = parsePlanIds(value);
  const available = new Set(availableIds.map((id) => id.toLowerCase()));
  const ids = requested.filter((id) => isPlanId(id) && available.has(id)).slice(0, MAX_SELECTED_PLANS);
  return { ids, removedCount: requested.length - ids.length };
}

export function togglePlanSelection(ids: readonly string[], planId: string): { ids: string[]; limitReached: boolean } {
  if (ids.includes(planId)) {
    return { ids: ids.filter((id) => id !== planId), limitReached: false };
  }

  if (ids.length >= MAX_SELECTED_PLANS) {
    return { ids: [...ids], limitReached: true };
  }

  return { ids: [...ids, planId], limitReached: false };
}
