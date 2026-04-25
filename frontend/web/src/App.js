import React, { useEffect, useState } from "react";
import "./App.css";

const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_BASE =
  process.env.REACT_APP_API_BASE ||
  (isLocalHost ? "http://127.0.0.1:8002" : window.location.origin);

function App() {
  const [stocks, setStocks] = useState([]);
  const [profile, setProfile] = useState({
    age: 30,
    income: 60000,
    investment_amount: 5000,
    risk_preference: "Medium",
    time_period_years: 5,
    financial_goals: "Wealth growth"
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState({ rating: 5, comments: "" });
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const [registerData, setRegisterData] = useState({ name: "", email: "", password: "" });
  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [user, setUser] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [ingestStatus, setIngestStatus] = useState("");
  const [apiStatus, setApiStatus] = useState("checking");
  const [apiError, setApiError] = useState("");
  const [recommendError, setRecommendError] = useState("");
  const [csvError, setCsvError] = useState("");
  const [csvStatus, setCsvStatus] = useState("");
  const [metricsError, setMetricsError] = useState("");
  const [kse100, setKse100] = useState([]);
  const [kse100Error, setKse100Error] = useState("");
  const [equityReports, setEquityReports] = useState([]);
  const [equityReportsMeta, setEquityReportsMeta] = useState({ updated_at: null, count: 0 });
  const [equityReportError, setEquityReportError] = useState("");
  const [equityReportFile, setEquityReportFile] = useState(null);
  const [equityReportStatus, setEquityReportStatus] = useState("");
  const [reportMeta, setReportMeta] = useState({
    projectTitle: "Designing and Development of AI Agent for Investment Portfolio Recommendation",
    team: "FYP Team",
    supervisor: "Supervisor Name",
    institute: "Institute Name",
    date: new Date().toISOString().slice(0, 10)
  });
  const [showAllRecs, setShowAllRecs] = useState(false);
  const [stocksPage, setStocksPage] = useState(1);
  const stocksPerPage = 50;
  const topReportDrivenRecs = result?.recommendations
    ? [...result.recommendations]
        .filter((rec) => rec.report_target_view || typeof rec.fundamental_score === "number")
        .sort((a, b) => b.allocation - a.allocation)
        .slice(0, 5)
    : [];

  useEffect(() => {
    fetch(`${API_BASE}/`)
      .then(response => response.json())
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));

    fetch(`${API_BASE}/stocks`)
      .then(response => response.json())
      .then(data => {
        setStocks(data.data);
        setApiError("");
      })
      .catch(error => {
        console.error("Error:", error);
        setApiError("Unable to load market data. Check backend status.");
      });

    fetch(`${API_BASE}/kse100`)
      .then(response => response.json())
      .then(data => {
        setKse100(data.data || []);
        setKse100Error("");
      })
      .catch(error => {
        console.error("Error:", error);
        setKse100Error("Unable to load KSE-100 data.");
      });

    fetch(`${API_BASE}/equity-reports`)
      .then(response => response.json())
      .then(data => {
        setEquityReports(data.reports || []);
        setEquityReportsMeta({
          updated_at: data.updated_at || null,
          count: data.count || 0
        });
        setEquityReportError("");
      })
      .catch(error => {
        console.error("Error:", error);
        setEquityReportError("Unable to load equity research reports.");
      });
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({
      ...prev,
      [name]: name === "risk_preference" || name === "financial_goals" ? value : Number(value)
    }));
  };

  const submitProfile = (e) => {
    e.preventDefault();
    setLoading(true);
    setRecommendError("");
    fetch(`${API_BASE}/recommendation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile)
    })
      .then(response => response.json())
      .then(data => {
        setResult(data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error:", error);
        setRecommendError("Recommendation failed. Check backend connection.");
        setLoading(false);
      });
  };

  const registerUser = (e) => {
    e.preventDefault();
    fetch(`${API_BASE}/users/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(registerData)
    })
      .then(response => response.json())
      .then(data => {
        if (!data.error) {
          setUser(data);
        }
      })
      .catch(error => console.error("Error:", error));
  };

  const loginUser = (e) => {
    e.preventDefault();
    fetch(`${API_BASE}/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(loginData)
    })
      .then(response => response.json())
      .then(data => {
        if (!data.error) {
          setUser(data);
        }
      })
      .catch(error => console.error("Error:", error));
  };

  const savePortfolio = () => {
    if (!user || !result) return;
    fetch(`${API_BASE}/portfolios/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: user.user_id,
        profile,
        recommendation: result
      })
    })
      .then(response => response.json())
      .then(() => setSaveStatus("Portfolio saved."))
      .catch(error => console.error("Error:", error));
  };

  const uploadCsv = (e) => {
    e.preventDefault();
    if (!csvFile) return;
    setCsvError("");
    setCsvStatus("Uploading market CSV...");
    const formData = new FormData();
    formData.append("file", csvFile);
    fetch(`${API_BASE}/market/upload`, {
      method: "POST",
      body: formData
    })
      .then(response => response.json())
      .then((data) => {
        setCsvStatus(`Upload complete: ${data.inserted || 0} market rows added.`);
        setCsvFile(null);
        return fetch(`${API_BASE}/stocks`);
      })
      .then(response => response.json())
      .then((data) => {
        setStocks(data.data || []);
      })
      .catch(error => {
        console.error("Error:", error);
        setCsvStatus("");
        setCsvError("CSV upload failed.");
      });
  };

  const loadMetrics = () => {
    setMetricsError("");
    fetch(`${API_BASE}/models/metrics`)
      .then(response => response.json())
      .then(data => setMetrics(data))
      .catch(error => {
        console.error("Error:", error);
        setMetricsError("Unable to load metrics.");
      });
  };

  const runIngestion = () => {
    setIngestStatus("Running ingestion...");
    fetch(`${API_BASE}/ingest/run`, { method: "POST" })
      .then(response => response.json())
      .then(data => {
        if (data.status === "ok") {
          setIngestStatus("Ingestion completed.");
        } else {
          setIngestStatus("Ingestion failed.");
        }
      })
      .catch(error => {
        console.error("Error:", error);
        setIngestStatus("Ingestion failed.");
      });
  };

  const uploadEquityReports = (e) => {
    e.preventDefault();
    if (!equityReportFile) return;
    setEquityReportStatus("Uploading research reports...");
    const formData = new FormData();
    formData.append("file", equityReportFile);
    fetch(`${API_BASE}/equity-reports/upload`, {
      method: "POST",
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "ok") {
          setEquityReportStatus(`Upload complete: ${data.accepted_reports} reports accepted.`);
          return fetch(`${API_BASE}/equity-reports`);
        }
        throw new Error(data.message || "Upload failed");
      })
      .then(response => response.json())
      .then(data => {
        setEquityReports(data.reports || []);
        setEquityReportsMeta({
          updated_at: data.updated_at || null,
          count: data.count || 0
        });
        setEquityReportFile(null);
      })
      .catch(error => {
        console.error("Error:", error);
        setEquityReportStatus("Upload failed.");
      });
  };

  const exportCsv = () => {
    if (!result) return;
    const headers = [
      "symbol",
      "allocation",
      "expected_return_pct",
      "volatility_pct",
      "var_95_pct",
      "beta",
      "action"
    ];
    const rows = result.recommendations.map(rec => [
      rec.symbol,
      rec.allocation,
      rec.expected_return_pct,
      rec.volatility_pct,
      rec.var_95_pct,
      rec.beta,
      rec.action
    ]);
    const content = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "portfolio_recommendation.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportPdf = () => {
    window.print();
  };

  const submitFeedback = (e) => {
    e.preventDefault();
    fetch("http://127.0.0.1:8000/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedback)
    })
      .then(() => setFeedbackSent(true))
      .catch(error => console.error("Error:", error));
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">IA</div>
          <div>
            <h1>AI Investment Portfolio Agent</h1>
            <p>Personalized portfolio recommendations with risk-return analysis.</p>
          </div>
        </div>
        <div className={`status-chip ${apiStatus}`}>
          API Status: {apiStatus === "online" ? "Online" : apiStatus === "offline" ? "Offline" : "Checking"}
        </div>
      </header>

      <section className="card">
        <h2>User Profile</h2>
        <form className="form-grid" onSubmit={submitProfile}>
          <label>
            Age
            <input type="number" name="age" value={profile.age} onChange={handleChange} min="18" />
          </label>
          <label>
            Income (USD)
            <input type="number" name="income" value={profile.income} onChange={handleChange} min="0" />
          </label>
          <label>
            Investment Amount (USD)
            <input type="number" name="investment_amount" value={profile.investment_amount} onChange={handleChange} min="0" />
          </label>
          <label>
            Risk Preference
            <select name="risk_preference" value={profile.risk_preference} onChange={handleChange}>
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
            </select>
          </label>
          <label>
            Time Period (years)
            <input type="number" name="time_period_years" value={profile.time_period_years} onChange={handleChange} min="1" />
          </label>
          <label>
            Financial Goals
            <input type="text" name="financial_goals" value={profile.financial_goals} onChange={handleChange} />
          </label>
          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? "Analyzing..." : "Get Recommendation"}
          </button>
        </form>
      </section>

      {result && (
        <section className="card printable">
          <h2>Recommendation Summary</h2>
          <div className="summary-grid">
            <div>
              <span>Risk Level</span>
              <strong>{result.risk_level}</strong>
            </div>
            <div>
              <span>Expected Return</span>
              <strong>{result.expected_return_pct}%</strong>
            </div>
            <div>
              <span>Portfolio Volatility</span>
              <strong>{result.portfolio_volatility_pct}%</strong>
            </div>
            <div>
              <span>Sharpe Ratio</span>
              <strong>{result.sharpe_ratio}</strong>
            </div>
          </div>
          <p className="advice">{result.rebalancing_advice}</p>
          <p className="advice">
            Recommendation mode: {equityReportsMeta.count > 0 ? "meeting reports + market data" : "market data only"}.
            {equityReportsMeta.count > 0 ? ` ${equityReportsMeta.count} research reports are currently available.` : " Upload 4-5 company reports to enable report-based suggestions."}
          </p>

          {topReportDrivenRecs.length > 0 && (
            <>
              <h3>Top Report-Driven Suggestions</h3>
              <div className="insight-grid">
                {topReportDrivenRecs.map((rec) => (
                  <article className="insight-card" key={rec.symbol}>
                    <div className="insight-head">
                      <strong>{rec.official_ticker}</strong>
                      <span className={`badge badge-${(rec.action || "hold").toLowerCase()}`}>{rec.action}</span>
                    </div>
                    <p>
                      Allocation {(rec.allocation * 100).toFixed(2)}% | FA Score{" "}
                      {typeof rec.fundamental_score === "number" ? rec.fundamental_score.toFixed(2) : "-"}
                    </p>
                    <p>Report View: {rec.report_target_view || "Not provided"}</p>
                    <p>{rec.reason}</p>
                  </article>
                ))}
              </div>
            </>
          )}

          <h3>Portfolio Allocation</h3>
          <div className="button-row">
            <button className="primary-btn" onClick={() => setShowAllRecs(!showAllRecs)}>
              {showAllRecs ? "Show Top 20" : "Show All"}
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Official</th>
                <th>Allocation</th>
                <th>Expected Return</th>
                <th>Volatility</th>
                <th>VaR 95%</th>
                <th>Beta</th>
                <th>FA Score</th>
                <th>Report View</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {[...result.recommendations]
                .sort((a, b) => b.allocation - a.allocation)
                .slice(0, showAllRecs ? result.recommendations.length : 20)
                .map((rec, idx) => (
                <tr key={idx}>
                  <td>{rec.symbol}</td>
                  <td>{rec.official_ticker}</td>
                  <td>{(rec.allocation * 100).toFixed(4)}%</td>
                  <td>{rec.expected_return_pct}%</td>
                  <td>{rec.volatility_pct}%</td>
                  <td>{rec.var_95_pct}%</td>
                  <td>{rec.beta}</td>
                  <td>{typeof rec.fundamental_score === "number" ? rec.fundamental_score.toFixed(2) : "-"}</td>
                  <td>{rec.report_target_view || "-"}</td>
                  <td>{rec.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button className="primary-btn" onClick={savePortfolio} disabled={!user}>
            {user ? "Save Portfolio" : "Login to Save"}
          </button>
          <div className="button-row">
            <button className="primary-btn" onClick={exportCsv}>Export CSV</button>
            <button className="primary-btn" onClick={exportPdf}>Print PDF</button>
          </div>
          {saveStatus && <p className="advice">{saveStatus}</p>}
          {recommendError && <p className="error">{recommendError}</p>}
        </section>
      )}

      <section className="card printable report-card">
        <h2>FYP Report Export</h2>
        <p className="advice">Fill details and click Print PDF to generate your report cover + summary.</p>
        <div className="form-grid">
          <label>
            Project Title
            <input
              type="text"
              value={reportMeta.projectTitle}
              onChange={(e) => setReportMeta({ ...reportMeta, projectTitle: e.target.value })}
            />
          </label>
          <label>
            Team
            <input
              type="text"
              value={reportMeta.team}
              onChange={(e) => setReportMeta({ ...reportMeta, team: e.target.value })}
            />
          </label>
          <label>
            Supervisor
            <input
              type="text"
              value={reportMeta.supervisor}
              onChange={(e) => setReportMeta({ ...reportMeta, supervisor: e.target.value })}
            />
          </label>
          <label>
            Institute
            <input
              type="text"
              value={reportMeta.institute}
              onChange={(e) => setReportMeta({ ...reportMeta, institute: e.target.value })}
            />
          </label>
          <label>
            Date
            <input
              type="date"
              value={reportMeta.date}
              onChange={(e) => setReportMeta({ ...reportMeta, date: e.target.value })}
            />
          </label>
        </div>
        <div className="report-preview">
          <h3>{reportMeta.projectTitle}</h3>
          <p><strong>Team:</strong> {reportMeta.team}</p>
          <p><strong>Supervisor:</strong> {reportMeta.supervisor}</p>
          <p><strong>Institute:</strong> {reportMeta.institute}</p>
          <p><strong>Date:</strong> {reportMeta.date}</p>
          <p className="advice">
            Summary: AI agent collects market data, profiles user risk, forecasts returns,
            optimizes portfolio allocation, and provides recommendation with risk metrics.
          </p>
        </div>
        <button className="primary-btn" onClick={exportPdf}>Print PDF</button>
      </section>

      <section className="card">
        <h2>User Accounts</h2>
        <div className="form-grid">
          <form onSubmit={registerUser}>
            <label>
              Name
              <input
                type="text"
                value={registerData.name}
                onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={registerData.email}
                onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={registerData.password}
                onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
              />
            </label>
            <button type="submit" className="primary-btn">Register</button>
          </form>
          <form onSubmit={loginUser}>
            <label>
              Email
              <input
                type="email"
                value={loginData.email}
                onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
              />
            </label>
            <button type="submit" className="primary-btn">Login</button>
          </form>
        </div>
        {user && <p className="advice">Logged in as {user.name} ({user.email})</p>}
      </section>

      <section className="card">
        <h2>Market Data Upload</h2>
        <form className="form-grid" onSubmit={uploadCsv}>
          <label>
            CSV File
            <input type="file" accept=".csv" onChange={(e) => setCsvFile(e.target.files[0])} />
          </label>
          <button type="submit" className="primary-btn">Upload CSV</button>
        </form>
        <p className="advice">CSV columns: symbol, price, volume, timestamp</p>
        <button className="primary-btn" onClick={runIngestion}>Run Ingestion Now</button>
        {ingestStatus && <p className="advice">{ingestStatus}</p>}
        {csvStatus && <p className="advice">{csvStatus}</p>}
        {csvError && <p className="error">{csvError}</p>}
        {apiError && <p className="error">{apiError}</p>}
      </section>

      <section className="card">
        <h2>Model Training Metrics</h2>
        <button className="primary-btn" onClick={loadMetrics}>Load Metrics</button>
        {metrics && metrics.results && (
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>MAE</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics.results).map(([name, value]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{value.mae}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {metrics && metrics.status === "missing" && (
          <p className="advice">{metrics.message}</p>
        )}
        {metricsError && <p className="error">{metricsError}</p>}
      </section>

      <section className="card">
        <h2>Equity Research Reports</h2>
        <p className="advice">
          Loaded reports: {equityReportsMeta.count}
          {equityReportsMeta.updated_at ? ` | Updated: ${equityReportsMeta.updated_at}` : ""}
        </p>
        <form className="form-grid" onSubmit={uploadEquityReports}>
          <label>
            Research CSV or JSON File
            <input type="file" accept=".csv,.json,text/csv,application/json" onChange={(e) => setEquityReportFile(e.target.files[0])} />
          </label>
          <button type="submit" className="primary-btn">Upload Reports</button>
        </form>
        {equityReportStatus && <p className="advice">{equityReportStatus}</p>}
        {equityReportError && <p className="error">{equityReportError}</p>}
        {equityReports.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Company</th>
                <th>Sector</th>
                <th>FA Score</th>
                <th>Target View</th>
                <th>Confidence</th>
                <th>Thesis</th>
              </tr>
            </thead>
            <tbody>
              {equityReports.slice(0, 20).map((row, idx) => (
                <tr key={idx}>
                  <td>{row.symbol}</td>
                  <td>{row.company_name || "-"}</td>
                  <td>{row.sector || "-"}</td>
                  <td>{typeof row.fundamental_score === "number" ? row.fundamental_score.toFixed(2) : "-"}</td>
                  <td>{row.target_view || "-"}</td>
                  <td>{typeof row.confidence_score === "number" ? row.confidence_score : "-"}</td>
                  <td>{row.thesis ? `${row.thesis.slice(0, 90)}${row.thesis.length > 90 ? "..." : ""}` : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Feedback</h2>
        <form className="form-grid" onSubmit={submitFeedback}>
          <label>
            Rating (1-5)
            <input
              type="number"
              min="1"
              max="5"
              value={feedback.rating}
              onChange={(e) => setFeedback({ ...feedback, rating: Number(e.target.value) })}
            />
          </label>
          <label>
            Comments
            <input
              type="text"
              value={feedback.comments}
              onChange={(e) => setFeedback({ ...feedback, comments: e.target.value })}
            />
          </label>
          <button type="submit" className="primary-btn">
            {feedbackSent ? "Thanks for the feedback" : "Send Feedback"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Market Data (PSX sample)</h2>
        <p className="advice">Showing {Math.min(stocks.length, stocksPerPage)} of {stocks.length} stocks</p>
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Official</th>
              <th>Price</th>
              <th>Volume</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {stocks
              .slice((stocksPage - 1) * stocksPerPage, stocksPage * stocksPerPage)
              .map((row, index) => (
              <tr key={index}>
                <td>{row.symbol}</td>
                <td>{row.official_ticker}</td>
                <td>{row.price}</td>
                <td>{row.volume}</td>
                <td>{row.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="button-row">
          <button 
            className="primary-btn" 
            onClick={() => setStocksPage(Math.max(1, stocksPage - 1))}
            disabled={stocksPage === 1}
          >
            Previous
          </button>
          <span>Page {stocksPage} of {Math.ceil(stocks.length / stocksPerPage)}</span>
          <button 
            className="primary-btn" 
            onClick={() => setStocksPage(stocksPage + 1)}
            disabled={stocksPage >= Math.ceil(stocks.length / stocksPerPage)}
          >
            Next
          </button>
        </div>
      </section>

      <section className="card">
        <h2>KSE-100 Companies (PSX)</h2>
        {kse100Error && <p className="error">{kse100Error}</p>}
        {kse100.length > 0 ? (
          <table>
            <thead>
              <tr>
                {Object.keys(kse100[0]).map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {kse100.map((row, idx) => (
                <tr key={idx}>
                  {Object.values(row).map((value, i) => (
                    <td key={i}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="advice">Loading KSE-100 data...</p>
        )}
      </section>
    </div>
  );
}

export default App;
