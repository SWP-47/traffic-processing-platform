import { BrowserRouter, Routes, Route } from "react-router";
import "@/styles/global.css";

import Dashboard from "@/pages/Dashboard/Dashboard";
import Login from "@/pages/Login/Login";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;