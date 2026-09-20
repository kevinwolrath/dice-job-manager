import { useState } from "react";
import { AuthProvider, useAuth } from "./auth.jsx";
import LoginForm from "./components/LoginForm.jsx";
import UserBadge from "./components/UserBadge.jsx";
import JobsPanel from "./components/JobsPanel.jsx";
import CreateJobForm from "./components/CreateJobForm.jsx";
import AdminPanel from "./components/AdminPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";

function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);
  return (
    <div className="dashboard">
      <div className="columns">
        <CreateJobForm onCreated={() => setRefreshKey((k) => k + 1)} />
        <JobsPanel refreshKey={refreshKey} />
      </div>
      <AdminPanel />
    </div>
  );
}

const VIEWS = [
  { id: "jobs", label: "Jobs" },
  { id: "chat", label: "Chat" },
];

function AppInner() {
  const { token } = useAuth();
  const [view, setView] = useState("jobs");
  const isChatView = token && view === "chat";

  return (
    <div className={`app${isChatView ? " app-chat" : ""}`}>
      <header>
        <h1>dice-job-manager test client</h1>
        {!isChatView && (
          <p className="hint">
            A minimal, un-styled UI for exercising dice-user-service, dice-stock-service, and
            dice-job-service directly. Open this page in two browser tabs and log each into a
            different demo user to watch cross-user isolation hold in real time — not just in
            PowerShell.
          </p>
        )}
      </header>
      {token ? (
        <>
          <UserBadge />
          <nav className="main-nav">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                type="button"
                className={view === v.id ? "active" : ""}
                onClick={() => setView(v.id)}
              >
                {v.label}
              </button>
            ))}
          </nav>
          {/* Both views stay mounted and are just hidden/shown — switching
              tabs shouldn't reset an in-progress conversation or the jobs
              list's own local state. */}
          <div style={{ display: view === "jobs" ? "block" : "none" }}>
            <Dashboard />
          </div>
          <div style={{ display: view === "chat" ? "flex" : "none", flexDirection: "column" }}>
            <ChatPanel />
          </div>
        </>
      ) : (
        <LoginForm />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
