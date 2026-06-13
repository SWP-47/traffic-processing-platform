import { BrowserRouter, Routes, Route } from "react-router";
import "@/styles/global.css";

import Dashboard from "@/pages/Dashboard/Dashboard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route index element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;