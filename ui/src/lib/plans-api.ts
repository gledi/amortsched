import { api, downloadFile } from "./api-client";
import type {
  Adjustments,
  HousingCosts,
  InterestRateApplication,
  LoanType,
  Plan,
  PlanComparison,
  Schedule,
} from "./types";

type NumericHousingCosts = { [K in keyof HousingCosts]: K extends "property_value" ? number | null : number };

export interface PlanPayload {
  name: string;
  loan_type: LoanType;
  currency: string;
  amount: number;
  interest_rate: number;
  term: {
    years: number;
    months: number;
  };
  start_date?: string;
  lender: string;
  upfront_fees: number;
  early_payment_fees: {
    fixed: number;
    percent: number;
  };
  housing_costs: NumericHousingCosts | Record<string, never>;
  interest_rate_application: InterestRateApplication;
}

export type CreatePlanPayload = PlanPayload & Partial<Adjustments>;
export type UpdatePlanPayload = Partial<PlanPayload>;

export const plansApi = {
  listPlans: () => api<Plan[]>("/plans"),

  getPlan: (planId: string) => api<Plan>(`/plans/${planId}`),

  previewComparison: (planIds: string[], horizonMonths?: number) =>
    api<PlanComparison>("/plan-comparisons/preview", {
      method: "POST",
      body: { plan_ids: planIds, horizon_months: horizonMonths ?? null },
    }),

  createPlan: (data: CreatePlanPayload) =>
    api<Plan>("/plans", {
      method: "POST",
      body: data,
    }),

  updatePlan: (planId: string, data: UpdatePlanPayload) =>
    api<Plan>(`/plans/${planId}`, {
      method: "PATCH",
      body: data,
    }),

  replaceAdjustments: (planId: string, data: Adjustments) =>
    api<Plan>(`/plans/${planId}/adjustments`, {
      method: "PUT",
      body: data,
    }),

  duplicatePlan: (planId: string) => api<Plan>(`/plans/${planId}/duplicate`, { method: "POST" }),

  exportScheduleCsv: (planId: string) => downloadFile(`/plans/${planId}/schedule.csv`, "schedule.csv"),

  deletePlan: (planId: string) =>
    api<void>(`/plans/${planId}`, {
      method: "DELETE",
    }),

  savePlan: (planId: string) =>
    api<Plan>(`/plans/${planId}/save`, {
      method: "POST",
    }),

  listSchedules: (planId: string) => api<Schedule[]>(`/plans/${planId}/schedules`),

  generateSchedule: (planId: string) =>
    api<Schedule>(`/plans/${planId}/schedules`, {
      method: "POST",
    }),

  getSchedule: (planId: string, scheduleId: string) => api<Schedule>(`/plans/${planId}/schedules/${scheduleId}`),

  saveSchedule: (planId: string, scheduleId: string) =>
    api<Schedule>(`/plans/${planId}/schedules/${scheduleId}/save`, {
      method: "POST",
    }),

  deleteSchedule: (planId: string, scheduleId: string) =>
    api<void>(`/plans/${planId}/schedules/${scheduleId}`, {
      method: "DELETE",
    }),
};
