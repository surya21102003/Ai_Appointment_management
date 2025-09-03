import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Predict from "./pages/Predict";
import Schedule from "./pages/Schedule";
import Train from "./pages/Train";

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="p-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/predict" element={<Predict />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/train" element={<Train />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
