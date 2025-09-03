import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Home() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/health")
      .then(res => setStatus(res.data.status))
      .catch(() => setStatus("API not reachable"));
  }, []);

  return (
    <div className="text-center mt-20">
      <h2 className="text-3xl font-bold text-blue-700">
        Preventing Health Risks with AI-powered Appointment Management
      </h2>
      <p className="mt-4 text-gray-600">
        This system predicts patient disease & attendance risks and suggests smart scheduling.
      </p>
      <div className="mt-6">
        <span className="font-semibold">Backend Status: </span>
        <span className={status === "ok" ? "text-green-600" : "text-red-600"}>
          {status || "Checking..."}
        </span>
      </div>
    </div>
  );
}
