const BASE_URL = "http://127.0.0.1:8000";

// ---------------- Upload Market
export const uploadMarket = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/market/upload`, {
    method: "POST",
    body: formData,
  });

  return res.json();
};

// ---------------- Upload Research
export const uploadResearch = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/equity-reports/upload`, {
    method: "POST",
    body: formData,
  });

  return res.json();
};

// ---------------- Recommendation
export const getRecommendation = async () => {
  const res = await fetch(`${BASE_URL}/recommendation`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  return res.json();
};

// ---------------- History
export const getHistory = async () => {
  const res = await fetch(`${BASE_URL}/history`);
  return res.json();
};