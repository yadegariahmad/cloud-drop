import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useUploadFile } from "@/api/files";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/toast";
import { formatBytes } from "@/lib/utils";

interface UploadItem {
  file: File;
  progress: number;
  status: "uploading" | "done" | "error";
}

export function DropZone() {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const uploadFile = useUploadFile();
  const { toast } = useToast();

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => {
        setUploads((prev) => [
          ...prev,
          { file, progress: 0, status: "uploading" },
        ]);

        uploadFile.mutate(
          {
            file,
            onProgress: (pct) => {
              setUploads((prev) =>
                prev.map((u) =>
                  u.file === file ? { ...u, progress: pct } : u
                )
              );
            },
          },
          {
            onSuccess: () => {
              setUploads((prev) =>
                prev.map((u) =>
                  u.file === file ? { ...u, status: "done", progress: 100 } : u
                )
              );
              toast({ title: "Upload complete", description: file.name });
              setTimeout(() => {
                setUploads((prev) => prev.filter((u) => u.file !== file));
              }, 2000);
            },
            onError: () => {
              setUploads((prev) =>
                prev.map((u) =>
                  u.file === file ? { ...u, status: "error" } : u
                )
              );
              toast({
                title: "Upload failed",
                description: file.name,
                variant: "destructive",
              });
            },
          }
        );
      });
    },
    [uploadFile, toast, uploads.length]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2">
          <svg
            className="w-10 h-10 text-muted-foreground"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="text-muted-foreground">
            {isDragActive
              ? "Drop files here..."
              : "Drag & drop files, or click to select"}
          </p>
        </div>
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((u, i) => (
            <div
              key={`${u.file.name}-${i}`}
              className="flex items-center gap-3 p-3 rounded-lg bg-muted/50"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{u.file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatBytes(u.file.size)}
                </p>
              </div>
              <div className="w-32">
                <Progress value={u.progress} className="h-2" />
              </div>
              <span className="text-xs text-muted-foreground w-12 text-right">
                {u.status === "done"
                  ? "Done"
                  : u.status === "error"
                    ? "Error"
                    : `${u.progress}%`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
