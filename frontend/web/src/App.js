import React, { useState } from "react";
import "./App.css";

function App() {
  const [form, setForm] = useState({
    age: 25,
    income: 100000,
    investment_amount: 20000,
    risk_preference: "Medium",
    financial_goals: "Wealth growth",
    time_period_years: 5
  });

  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const uploadFile = async (file, endpoint) => {
    const formData = new FormData();
    formData.append("file", file);

    await fetch(`http://127.0.0.1:8000/${endpoint}`, {
      method: "POST",
      body: formData
    });
  };

  const getRecommendation = async () => {
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/recommendation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });

      const data = await res.json();
      setPortfolio(data.portfolio);
    } catch (err) {
      alert("Backend not responding");
    }

    setLoading(false);
  };

  return (
    <div className="dashboard">

      {/* HEADER */}
      <div className="header">
        <h1>🤖 AI Investment Portfolio Advisor</h1>
        <p>Smart Portfolio Optimization System</p>
      </div>

      {/* UPLOAD SECTION */}
      <div className="grid">

        <div className="card">
          <h3>📊 Market Data</h3>
          <input type="file" onChange={(e) => uploadFile(e.target.files[0], "market/upload")} />
        </div>

        <div className="card">
          <h3>📑 Research Data</h3>
          <input type="file" onChange={(e) => uploadFile(e.target.files[0], "equity-reports/upload")} />
        </div>

      </div>

      {/* USER INPUT */}
      <div className="card large">
        <h2>👤 Investor Profile</h2>

        <div className="form-grid">

          <input name="age" placeholder="Age" onChange={handleChange} />
          <input name="income" placeholder="Income" onChange={handleChange} />
          <input name="investment_amount" placeholder="Investment Amount" onChange={handleChange} />

          <select name="risk_preference" onChange={handleChange}>
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </select>

          <input name="financial_goals" placeholder="Financial Goals" onChange={handleChange} />
          <input name="time_period_years" placeholder="Time Period (Years)" onChange={handleChange} />

        </div>

        <button onClick={getRecommendation} className="btn">
          {loading ? "Processing..." : "Get Recommendation"}
        </button>
      </div>

      {/* OUTPUT */}
      {portfolio && (
        <div className="card large">
          <h2>📈 Recommended Portfolio</h2>

          <div className="portfolio-grid">

            {portfolio.map((p, i) => (
              <div key={i} className="stock-card">
                <h3>{p.symbol}</h3>

                <div className="bar">
                  <div style={{ width: `${p.allocation_pct}%` }} className="fill"></div>
                </div>

                <p>📊 Allocation: {p.allocation_pct}%</p>
                <p>⭐ Score: {p.score}</p>

                <small>{p.reasons.join(" • ")}</small>
              </div>
            ))}

          </div>

        </div>
      )}

    </div>
  );
}

export default App;