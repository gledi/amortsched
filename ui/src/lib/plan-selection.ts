const MAX_SELECTED_PLANS = 4;
const MIN_SELECTED_PLANS = 2;

export function parsePlanIds(value: unknown): string[] {
  if (typeof value !== "string") {
    return [];
  }

  return [
    ...new Set(
      value
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean),
    ),
  ];
}

export function isComparableSelection(ids: readonly string[]): boolean {
  return ids.length >= MIN_SELECTED_PLANS;
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
