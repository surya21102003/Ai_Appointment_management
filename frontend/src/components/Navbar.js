import React from "react";
import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="bg-blue-600 text-white p-4 shadow-md sticky top-0 z-50">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="font-bold text-xl">🏥 Smart Health Manager</h1>
        <div className="space-x-6">
          <Link to="/" className="hover:underline">Home</Link>
          <Link to="/predict" className="hover:underline">Predict Risk</Link>
          <Link to="/schedule" className="hover:underline">Schedule</Link>
          <Link to="/train" className="hover:underline">Train Model</Link>
        </div>
      </div>
    </nav>
  );
}
