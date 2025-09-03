import React from "react";

export default function ResultCard({ title, data }) {
  return (
    <div className="mt-6 p-4 border rounded bg-gray-50">
      <h3 className="text-lg font-bold text-blue-700">{title}</h3>
      <pre className="text-sm mt-2 bg-white p-2 rounded overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
