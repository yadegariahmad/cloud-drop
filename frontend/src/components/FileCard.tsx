import { useState } from "react";
import type { FileItem } from "@/api/files";
import { useDeleteFile } from "@/api/files";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { ShareModal } from "./ShareModal";
import { useToast } from "@/components/ui/toast";
import { formatBytes, formatDate } from "@/lib/utils";

const mimeIcons: Record<string, string> = {
  "image/": "photo",
  "video/": "video",
  "audio/": "audio",
  "application/pdf": "PDF",
  "text/": "text",
};

function getFileIcon(mime: string | null): string {
  if (!mime) return "file";
  for (const [prefix, icon] of Object.entries(mimeIcons)) {
    if (mime.startsWith(prefix)) return icon;
  }
  return "file";
}

export function FileCard({ file }: { file: FileItem }) {
  const [shareOpen, setShareOpen] = useState(false);
  const deleteFile = useDeleteFile();
  const { toast } = useToast();

  const handleDelete = () => {
    deleteFile.mutate(file.id, {
      onSuccess: () => toast({ title: "File deleted", description: file.filename }),
      onError: () =>
        toast({ title: "Delete failed", variant: "destructive" }),
    });
  };

  return (
    <>
      <Card className="group hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <span className="text-xs font-bold text-primary uppercase">
                  {getFileIcon(file.mime_type)}
                </span>
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{file.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {formatBytes(file.size_bytes)} &middot; {formatDate(file.created_at)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <Badge variant="secondary" className="text-xs">
                {file.mime_type?.split("/")[1] || "file"}
              </Badge>
              <DropdownMenu
                trigger={
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
                    </svg>
                  </Button>
                }
              >
                <DropdownMenuItem onClick={() => setShareOpen(true)}>
                  Share
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={handleDelete}
                >
                  Delete
                </DropdownMenuItem>
              </DropdownMenu>
            </div>
          </div>
        </CardContent>
      </Card>

      <ShareModal
        fileId={file.id}
        fileName={file.filename}
        open={shareOpen}
        onOpenChange={setShareOpen}
      />
    </>
  );
}
