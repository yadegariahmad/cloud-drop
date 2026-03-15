import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { apiClient } from "./client";

interface FileItem {
  id: string;
  owner_id: string;
  filename: string;
  s3_key: string;
  mime_type: string | null;
  size_bytes: number;
  status: string;
  created_at: string;
  updated_at: string;
}

interface FileListResponse {
  files: FileItem[];
  total: number;
}

interface UploadUrlResponse {
  upload_url: string;
  file_id: string;
  s3_key: string;
}

export type { FileItem };

export const fileKeys = {
  all: ["files"] as const,
  list: () => [...fileKeys.all, "list"] as const,
};

export function useFiles() {
  return useQuery({
    queryKey: fileKeys.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<FileListResponse>("/files");
      return data;
    },
  });
}

export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (pct: number) => void;
    }) => {
      // 1. Get presigned URL
      const { data } = await apiClient.post<UploadUrlResponse>("/files/upload-url", {
        filename: file.name,
        size_bytes: file.size,
        mime_type: file.type || "application/octet-stream",
      });

      // 2. Upload directly to S3
      await axios.put(data.upload_url, file, {
        headers: { "Content-Type": file.type || "application/octet-stream" },
        onUploadProgress: (e) => {
          if (e.total && onProgress) {
            onProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      });

      // 3. Confirm upload
      await apiClient.patch(`/files/${data.file_id}/confirm`);
      return data;
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all });
    },
  });
}

export function useDeleteFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => apiClient.delete(`/files/${fileId}`),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all });
    },
  });
}
