import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { User } from "@/types";

export function useAuth() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const res = await api.get("/auth/me");
      return res.data as User;
    },
  });
}

export function useLogin() {
  return async (username: string, password: string) => {
    const res = await api.post("/auth/login", { username, password });
    const { token } = res.data;
    localStorage.setItem("token", token);
    return res.data;
  };
}

export function useLogout() {
  return () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };
}
