import { useState } from "react";
import { useCreateShare } from "@/api/shares";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

const TTL_OPTIONS = [
  { value: "1h", label: "1 Hour" },
  { value: "24h", label: "24 Hours" },
  { value: "7d", label: "7 Days" },
];

interface ShareModalProps {
  fileId: string;
  fileName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShareModal({ fileId, fileName, open, onOpenChange }: ShareModalProps) {
  const [ttl, setTtl] = useState("24h");
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const createShare = useCreateShare();
  const { toast } = useToast();

  const handleCreate = () => {
    createShare.mutate(
      { fileId, ttl },
      {
        onSuccess: (data) => {
          const publicUrl = `${window.location.origin}/share/${data.id}`;
          setShareUrl(publicUrl);
          navigator.clipboard.writeText(publicUrl).then(() => {
            toast({ title: "Link copied!", description: "Share link copied to clipboard" });
          });
        },
        onError: () => {
          toast({ title: "Failed to create share", variant: "destructive" });
        },
      }
    );
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setShareUrl(null);
      setTtl("24h");
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Share File</DialogTitle>
          <DialogDescription>
            Create a shareable link for &quot;{fileName}&quot;
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Link expires in</label>
            <Select options={TTL_OPTIONS} value={ttl} onValueChange={setTtl} />
          </div>

          <Button
            onClick={handleCreate}
            disabled={createShare.isPending}
            className="w-full"
          >
            {createShare.isPending ? "Generating..." : "Create Share Link"}
          </Button>

          {shareUrl && (
            <div className="p-3 rounded-lg bg-muted">
              <p className="text-xs text-muted-foreground mb-1">Share link:</p>
              <p className="text-sm font-mono break-all">{shareUrl}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => {
                  navigator.clipboard.writeText(shareUrl);
                  toast({ title: "Copied!" });
                }}
              >
                Copy Link
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
