import { useAuth } from "@/hooks/useAuth";
import { Navigate, Outlet } from 'react-router';
import Header from "./Header/Header";
import { useEffect, useState } from "react";
import authentication from "@/services/authentication";
import Loading from "@/pages/Loading/Loading";
import { UnitProvider } from "@/contexts/UnitContext/UnitProvider";

function PrivateRoute() {
  const { isAuthenticated } = useAuth();
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let cancelled = false;

    authentication.initialize().finally(() => {
      if (!cancelled) {
        setIsInitializing(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  if (isInitializing) {
    return <Loading />;
  }

  return isAuthenticated ? (
    <>
      <UnitProvider>
        <Header />
        <Outlet />
      </UnitProvider>
    </>
  ) : (
    <Navigate
      replace={true}
      to="/login"
      state={{ from: `${location.pathname}${location.search}` }}
    />
  )
}

export default PrivateRoute;