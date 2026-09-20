// Thin fetch wrapper for the three backend services. Deliberately not a
// generic axios-style client with interceptors — three base URLs and a
// handful of endpoints don't need that, and a plain fetch wrapper is easier
// to read for anyone new to this repo.
const USER_SERVICE_URL = "http://localhost:4101";
const STOCK_SERVICE_URL = "http://localhost:4102";
const JOB_SERVICE_URL = "http://localhost:4103";
const MCP_SERVICE_URL = "http://localhost:4104";

async function request(baseUrl, path, { method = "GET", token, body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no JSON body (e.g. a plain-text 500) — data stays null
  }

  if (!res.ok) {
    const detail = data && data.detail ? data.detail : `${res.status} ${res.statusText}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

export const userApi = {
  login: (username, password) =>
    request(USER_SERVICE_URL, "/login", { method: "POST", body: { username, password } }),
  me: (token) => request(USER_SERVICE_URL, "/me", { token }),
};

export const stockApi = {
  listMaterialTypes: (token) => request(STOCK_SERVICE_URL, "/material-types", { token }),
  createMaterialType: (token, description) =>
    request(STOCK_SERVICE_URL, "/material-types", { method: "POST", token, body: { description } }),
  deleteMaterialType: (token, id) =>
    request(STOCK_SERVICE_URL, `/material-types/${id}`, { method: "DELETE", token }),

  listProductionMethods: (token) => request(STOCK_SERVICE_URL, "/production-methods", { token }),
  createProductionMethod: (token, description) =>
    request(STOCK_SERVICE_URL, "/production-methods", { method: "POST", token, body: { description } }),
  deleteProductionMethod: (token, id) =>
    request(STOCK_SERVICE_URL, `/production-methods/${id}`, { method: "DELETE", token }),

  listDiceJobNumberColours: (token) => request(STOCK_SERVICE_URL, "/dice-job-number-colours", { token }),
  createDiceJobNumberColour: (token, name) =>
    request(STOCK_SERVICE_URL, "/dice-job-number-colours", {
      method: "POST",
      token,
      body: { dice_job_number_colour_name: name },
    }),
  deleteDiceJobNumberColour: (token, id) =>
    request(STOCK_SERVICE_URL, `/dice-job-number-colours/${id}`, { method: "DELETE", token }),
};

export const jobApi = {
  listMyJobs: (token) => request(JOB_SERVICE_URL, "/dice-jobs", { token }),
  createJob: (token, payload) => request(JOB_SERVICE_URL, "/dice-jobs", { method: "POST", token, body: payload }),
  deleteJob: (token, id) => request(JOB_SERVICE_URL, `/dice-jobs/${id}`, { method: "DELETE", token }),
};

// dice-mcp-server's /chat endpoint (Phase 6) — the demo path, not the raw
// MCP wire protocol. It runs the tool-calling loop against dice-ollama
// server-side and returns both the model's reply and the full trace of
// tool calls it made, so the UI can show exactly what the model looked at.
export const mcpApi = {
  chat: (token, message, history) =>
    request(MCP_SERVICE_URL, "/chat", { method: "POST", token, body: { message, history } }),
};
