import { api } from "./api-client";
import type {
  Plan,
  Schedule,
  User,
  InterestRateApplication,
} from "./types";

export interface CreatePlanPayload {
  name: string;
  amount: number;
  interest_rate: number;
  term: {
    years: number;
    months: number;
  };
  start_date?: string;
  early_payment_fees?: {
    fixed: number;
    percent: number;
  };
  interest_rate_application?: InterestRateApplication;
}

export interface UpdatePlanPayload {
  name?: string;
  amount?: number;
  interest_rate?: number;
  term?: {
    years: number;
    months: number;
  };
  start_date?: string;
  early_payment_fees?: {
    fixed: number;
    percent: number;
  };
  interest_rate_application?: InterestRateApplication;
}

export const plansApi = {
  getMe: () => api<User>("/users/me"),

  listPlans: () => api<Plan[]>("/plans"),

  getPlan: (planId: string) => api<Plan>(`/plans/${planId}`),

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

  deletePlan: (planId: string) =>
    api<void>(`/plans/${planId}`, {
      method: "DELETE",
    }),

  savePlan: (planId: string) =>
    api<Plan>(`/plans/${planId}/save`, {
      method: "POST",
    }),

  addExtraPayment: (planId: string, data: { date: string; amount: number }) =>
    api<Plan>(`/plans/${planId}/extra-payments`, {
      method: "POST",
      body: data,
    }),

  addRecurringExtraPayment: (
    planId: string,
    data: { start_date: string; amount: number; count: number },
  ) =>
    api<Plan>(`/plans/${planId}/recurring-extra-payments`, {
      method: "POST",
      body: data,
    }),

  addInterestRateChange: (
    planId: string,
    data: { effective_date: string; rate: number },
  ) =>
    api<Plan>(`/plans/${planId}/interest-rate-changes`, {
      method: "POST",
      body: data,
    }),

  listSchedules: (planId: string) =>
    api<Schedule[]>(`/plans/${planId}/schedules`),

  generateSchedule: (planId: string) =>
    api<Schedule>(`/plans/${planId}/schedules`, {
      method: "POST",
    }),

  getSchedule: (planId: string, scheduleId: string) =>
    api<Schedule>(`/plans/${planId}/schedules/${scheduleId}`),

  saveSchedule: (planId: string, scheduleId: string) =>
    api<Schedule>(`/plans/${planId}/schedules/${scheduleId}/save`, {
      method: "POST",
    }),

  deleteSchedule: (planId: string, scheduleId: string) =>
    api<void>(`/plans/${planId}/schedules/${scheduleId}`, {
      method: "DELETE",
    }),
};
