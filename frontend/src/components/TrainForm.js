import React, { useState } from "react";
import axios from "axios";
import ResultCard from "./ResultCard";

export default function TrainForm() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a CSV file");
      return;
    }
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await axios.post("http://127.0.0.1:8000/train/csv", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(res.data);
    } catch (err) {
      alert("Error uploading file");
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4">📊 Retrain Model</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input type="file" accept=".csv" onChange={handleFileChange} />
        <button className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 w-full">
          Upload & Retrain
        </button>
      </form>
      {result && <ResultCard title="Training Result" data={result} />}
    </div>
  );
}
