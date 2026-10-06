import { api, ApiError } from "./api-client";
import { setAccessToken } from "./auth";
import type { Profile, ProfileUpdate, User } from "./types";

interface TokenResponse {
  access_token: string;
}

interface AuthResponse extends TokenResponse {
  user: User;
}

export const accountApi = {
  async login(email: string, password: string): Promise<void> {
    const formData = new URLSearchParams({ username: email, password });
    const result = await api<TokenResponse>("/auth/token", { method: "POST", formData, anonymous: true });
    setAccessToken(result.access_token);
  },

  async register(data: { name: string; email: string; password: string }): Promise<User> {
    const result = await api<AuthResponse>("/auth/register", { method: "POST", body: data, anonymous: true });
    setAccessToken(result.access_token);
    return result.user;
  },

  verifyEmail: (token: string) => api<User>("/auth/verify-email", { method: "POST", body: { token }, anonymous: true }),

  requestPasswordReset: (email: string) =>
    api<void>("/auth/password-reset/request", { method: "POST", body: { email }, anonymous: true }),

  resetPassword: (token: string, password: string) =>
    api<void>("/auth/password-reset/confirm", { method: "POST", body: { token, password }, anonymous: true }),

  getMe: () => api<User>("/users/me"),

  updateMe: (name: string) => api<User>("/users/me", { method: "PATCH", body: { name } }),

  resendVerification: () => api<void>("/users/me/verification-email", { method: "POST" }),

  async getProfile(): Promise<Profile | null> {
    try {
      return await api<Profile>("/users/me/profile");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  updateProfile: (data: ProfileUpdate) => api<Profile>("/users/me/profile", { method: "PUT", body: data }),

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const result = await api<TokenResponse>("/users/me/password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    });
    setAccessToken(result.access_token);
  },

  async revokeOtherSessions(): Promise<void> {
    const result = await api<TokenResponse>("/users/me/sessions/revoke", { method: "POST" });
    setAccessToken(result.access_token);
  },

  exportData: () => api<unknown>("/users/me/export"),

  deleteAccount: (password: string) => api<void>("/users/me", { method: "DELETE", body: { password } }),
};
