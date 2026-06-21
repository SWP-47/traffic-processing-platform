import { useAuth } from "@/hooks/useAuth";
import type { ReactNode } from "react";
import { Navigate } from 'react-router';

function PrivateRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();

  return isAuthenticated ? (
    <>{children}</>
  ) : (
    <Navigate
      replace={true}
      to="/login"
      state={{ from: `${location.pathname}${location.search}` }}
    />
  )
}

export default PrivateRoute;