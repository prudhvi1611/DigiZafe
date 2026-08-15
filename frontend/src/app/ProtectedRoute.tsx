import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/lib/auth-store";
import { useMe } from "@/hooks/useAuth";

export function ProtectedRoute() {
  const access = useAuthStore((s) => s.accessToken);
  const refresh = useAuthStore((s) => s.refreshToken);
  const { isLoading, isError } = useMe(!!(access || refresh));

  if (!access && !refresh) return <Navigate to="/login" replace />;
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading session…
      </div>
    );
  }
  if (isError && !access) return <Navigate to="/login" replace />;
  return <Outlet />;
}
