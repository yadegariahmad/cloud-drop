import { apiClient } from "./client";
import { useAuthStore } from "@/stores/authStore";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function registerUser(email: string, password: string, fullName?: string) {
  const { data } = await apiClient.post<TokenResponse>("/auth/register", {
    email,
    password,
    full_name: fullName,
  });
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function loginUser(email: string, password: string) {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", {
    email,
    password,
  });
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logoutUser() {
  try {
    await apiClient.post("/auth/logout");
  } finally {
    useAuthStore.getState().logout();
  }
}

export async function fetchCurrentUser() {
  const { data } = await apiClient.get("/users/me");
  useAuthStore.getState().setUser(data);
  return data;
}
