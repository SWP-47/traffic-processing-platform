import { BrowserRouter, Routes, Route } from "react-router";
import "@/styles/global.css";

import Dashboard from "@/pages/Dashboard/Dashboard";
import Login from "@/pages/Login/Login";
import PrivateRoute from "./components/PrivateRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<PrivateRoute />}>
          <Route index element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;