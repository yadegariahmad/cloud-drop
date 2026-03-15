import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import { fileKeys } from "./files";

interface ShareItem {
  id: string;
  file_id: string;
  owner_id: string;
  expires_at: string;
  is_revoked: boolean;
  access_count: number;
  created_at: string;
  signed_url: string | null;
}

interface ShareListResponse {
  shares: ShareItem[];
  total: number;
}

interface PublicShare {
  id: string;
  filename: string;
  mime_type: string | null;
  size_bytes: number;
  signed_url: string;
}

export type { ShareItem, PublicShare };

export const shareKeys = {
  all: ["shares"] as const,
  list: () => [...shareKeys.all, "list"] as const,
  public: (id: string) => ["public-share", id] as const,
};

export function useShares() {
  return useQuery({
    queryKey: shareKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<ShareListResponse>("/shares");
      return data;
    },
  });
}

export function useCreateShare() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ fileId, ttl }: { fileId: string; ttl: string }) => {
      const { data } = await apiClient.post<ShareItem>("/shares", {
        file_id: fileId,
        ttl,
      });
      return data;
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: shareKeys.all });
      queryClient.invalidateQueries({ queryKey: fileKeys.all });
    },
  });
}

export function useRevokeShare() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (shareId: string) => apiClient.delete(`/shares/${shareId}`),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: shareKeys.all });
    },
  });
}

export function usePublicShare(shareId: string) {
  return useQuery({
    queryKey: shareKeys.public(shareId),
    queryFn: async () => {
      const { data } = await apiClient.get<PublicShare>(`/public/shares/${shareId}`);
      return data;
    },
    enabled: !!shareId,
  });
}
