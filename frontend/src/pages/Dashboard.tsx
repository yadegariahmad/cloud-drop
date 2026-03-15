import { useEffect } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useFiles } from "@/api/files";
import { fetchCurrentUser, logoutUser } from "@/api/auth";
import { DropZone } from "@/components/DropZone";
import { FileCard } from "@/components/FileCard";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { formatBytes } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const { data, isLoading } = useFiles();

  useEffect(() => {
    if (!user) fetchCurrentUser();
  }, [user]);

  const handleLogout = async () => {
    await logoutUser();
    navigate("/login");
  };

  const storagePercent = user
    ? Math.round((user.storage_used / user.storage_quota) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">CloudDrop</h1>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-muted-foreground hidden sm:inline">
                {user.email}
              </span>
            )}
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Storage usage */}
        {user && (
          <div className="max-w-md">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-muted-foreground">Storage</span>
              <span className="font-medium">
                {formatBytes(user.storage_used)} / {formatBytes(user.storage_quota)}
              </span>
            </div>
            <Progress value={storagePercent} className="h-2" />
          </div>
        )}

        {/* Upload zone */}
        <DropZone />

        <Separator />

        {/* File list */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Your Files</h2>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-20 rounded-lg" />
              ))}
            </div>
          ) : data?.files.length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.files.map((file) => (
                <FileCard key={file.id} file={file} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <svg
                className="w-12 h-12 mx-auto mb-4 opacity-50"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
              <p>No files yet. Upload your first file above!</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
