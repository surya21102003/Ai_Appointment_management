import React, { useState } from "react";
import axios from "axios";

const ScheduleForm = () => {
  const [form, setForm] = useState({
    age: "",
    sex: "male",
    chronic_conditions_count: "",
    previous_no_show_rate: "",
    days_until_appointment: "",
    sms_reminders_sent: "",
    distance_km: "",
    time_of_day: "morning",
    weekday: "mon",
    doctor_specialty: "general",
    symptoms_text: ""
  });

  const [candidateSlots, setCandidateSlots] = useState([{ slot: "2025-09-05 10:00" }]);

  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSlotChange = (index, e) => {
    const newSlots = [...candidateSlots];
    newSlots[index][e.target.name] = e.target.value;
    setCandidateSlots(newSlots);
  };

  const addSlot = () => {
    setCandidateSlots([...candidateSlots, { slot: "" }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post("http://127.0.0.1:8000/schedule", {
        patient: {
          age: Number(form.age),
          sex: form.sex,
          chronic_conditions_count: Number(form.chronic_conditions_count),
          previous_no_show_rate: Number(form.previous_no_show_rate),
          days_until_appointment: Number(form.days_until_appointment),
          sms_reminders_sent: Number(form.sms_reminders_sent),
          distance_km: Number(form.distance_km),
          time_of_day: form.time_of_day,
          weekday: form.weekday,
          doctor_specialty: form.doctor_specialty,
          symptoms_text: form.symptoms_text
        },
        candidate_slots: candidateSlots
      });
      setResult(res.data);
    } catch (err) {
      console.error(err);
      setResult({ error: "Scheduling failed. Check backend." });
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 bg-white rounded-xl shadow-md">
      <h2 className="text-xl font-bold mb-4 text-green-600">Smart Scheduling</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
        <input name="age" placeholder="Age" value={form.age} onChange={handleChange} className="border p-2 rounded" required />
        <select name="sex" value={form.sex} onChange={handleChange} className="border p-2 rounded">
          <option value="male">Male</option>
          <option value="female">Female</option>
        </select>
        <input name="chronic_conditions_count" placeholder="Chronic Conditions" value={form.chronic_conditions_count} onChange={handleChange} className="border p-2 rounded" required />
        <input name="previous_no_show_rate" placeholder="Previous No-Show Rate" value={form.previous_no_show_rate} onChange={handleChange} className="border p-2 rounded" required />
        <input name="days_until_appointment" placeholder="Days Until Appointment" value={form.days_until_appointment} onChange={handleChange} className="border p-2 rounded" required />
        <input name="sms_reminders_sent" placeholder="SMS Reminders Sent" value={form.sms_reminders_sent} onChange={handleChange} className="border p-2 rounded" required />
        <input name="distance_km" placeholder="Distance (km)" value={form.distance_km} onChange={handleChange} className="border p-2 rounded" required />
        <select name="time_of_day" value={form.time_of_day} onChange={handleChange} className="border p-2 rounded">
          <option value="morning">Morning</option>
          <option value="afternoon">Afternoon</option>
          <option value="evening">Evening</option>
        </select>
        <select name="weekday" value={form.weekday} onChange={handleChange} className="border p-2 rounded">
          <option value="mon">Mon</option>
          <option value="tue">Tue</option>
          <option value="wed">Wed</option>
          <option value="thu">Thu</option>
          <option value="fri">Fri</option>
        </select>
        <input name="doctor_specialty" placeholder="Doctor Specialty" value={form.doctor_specialty} onChange={handleChange} className="border p-2 rounded" required />
        <textarea name="symptoms_text" placeholder="Symptoms" value={form.symptoms_text} onChange={handleChange} className="border p-2 rounded col-span-2" />

        <div className="col-span-2">
          <h3 className="font-semibold mb-2">Candidate Slots</h3>
          {candidateSlots.map((slot, index) => (
            <input
              key={index}
              name="slot"
              placeholder="Enter slot (e.g., 2025-09-05 10:00)"
              value={slot.slot}
              onChange={(e) => handleSlotChange(index, e)}
              className="border p-2 rounded w-full mb-2"
            />
          ))}
          <button type="button" onClick={addSlot} className="bg-gray-500 text-white px-3 py-1 rounded">
            + Add Slot
          </button>
        </div>

        <button type="submit" className="col-span-2 bg-green-600 text-white p-2 rounded hover:bg-green-700">
          Schedule
        </button>
      </form>

      {result && (
        <div className="mt-4 p-4 border rounded bg-gray-50">
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default ScheduleForm;

