import { useParams } from "react-router-dom";
import { usePublicShare } from "@/api/shares";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBytes } from "@/lib/utils";

export default function ShareView() {
  const { shareId } = useParams<{ shareId: string }>();
  const { data, isLoading, error } = usePublicShare(shareId || "");

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !data) {
    const status = (error as any)?.response?.status;
    const message =
      status === 410
        ? "This share link has expired or been revoked."
        : status === 404
          ? "Share link not found."
          : "Something went wrong.";

    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md text-center">
          <CardHeader>
            <CardTitle className="text-xl">Unavailable</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{message}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isImage = data.mime_type?.startsWith("image/");

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-xl">CloudDrop</CardTitle>
          <p className="text-sm text-muted-foreground">Shared file</p>
        </CardHeader>
        <CardContent className="space-y-6">
          {isImage && (
            <div className="rounded-lg overflow-hidden border border-border">
              <img
                src={data.signed_url}
                alt={data.filename}
                className="w-full max-h-64 object-contain bg-muted"
              />
            </div>
          )}

          <div className="space-y-2">
            <h3 className="font-semibold text-lg break-all">{data.filename}</h3>
            <p className="text-sm text-muted-foreground">
              {formatBytes(data.size_bytes)}
              {data.mime_type && ` \u00B7 ${data.mime_type}`}
            </p>
          </div>

          <a href={data.signed_url} download={data.filename} className="block">
            <Button className="w-full" size="lg">
              Download File
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
