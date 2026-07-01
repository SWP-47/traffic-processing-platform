import { useAuth } from "@/hooks/useAuth";
import { Navigate, Outlet } from 'react-router';
import Header from "./Header/Header";

function PrivateRoute() {
  const { isAuthenticated } = useAuth();

  return isAuthenticated ? (
    <>
      <Header />
      <Outlet />
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