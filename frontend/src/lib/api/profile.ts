import axios from "axios";
import api from "@/lib/api";

export interface UserProfile {
  id: number;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  role: string;
  skills: string;
  is_active: boolean;
  created_at: string;
}

interface ProfileResponse {
  success: boolean;
  message?: string;
  data: UserProfile;
}

export async function fetchMyProfile(): Promise<UserProfile> {
  const response = await api.get<ProfileResponse>("me/");
  return response.data.data;
}

export async function updateMyName(firstName: string, lastName: string): Promise<UserProfile> {
  const response = await api.patch<ProfileResponse>("profile/", {
    first_name: firstName,
    last_name: lastName,
  });
  return response.data.data;
}

export function readProfileSaveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data && typeof data === "object") {
      const record = data as Record<string, unknown>;
      const messages = ["first_name", "last_name"].flatMap((key) => {
        const value = record[key];
        return Array.isArray(value) && typeof value[0] === "string" ? [value[0]] : [];
      });
      if (messages.length > 0) {
        return messages.join(" ");
      }
      if (typeof record.detail === "string" && record.detail.trim()) {
        return record.detail;
      }
    }
    if (error.response?.status === 401) {
      return "Sign in again to save your profile.";
    }
  }
  return "Could not save your profile.";
}
