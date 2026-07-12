import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Opportunity, AIAnalysis } from "@/types";

export function useOpportunities(search?: string) {
  return useQuery({
    queryKey: ["opportunities", search],
    queryFn: async () => {
      const res = await api.get("/opportunities", { params: { search } });
      return res.data.data as Opportunity[];
    },
  });
}

export function useOpportunity(id: number) {
  return useQuery({
    queryKey: ["opportunity", id],
    queryFn: async () => {
      const res = await api.get(`/opportunities/${id}`);
      return res.data as Opportunity;
    },
    enabled: !!id,
  });
}

export function useCreateOpportunity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      customerId: number;
      visitContent: string;
      aiAnalysis?: AIAnalysis;
    }) => {
      const res = await api.post("/opportunities", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });
}

export function useAnalyzeOpportunity() {
  return useMutation({
    mutationFn: async (content: string) => {
      const res = await api.post("/opportunities/analyze", { content });
      return res.data as AIAnalysis;
    },
  });
}
