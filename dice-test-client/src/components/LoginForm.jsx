import { useState } from "react";
import { useAuth } from "../auth.jsx";

const DEMO_USERS = [
  { username: "john", password: "john-demo-pw" },
  { username: "jane", password: "jane-demo-pw" },
  { username: "admin", password: "admin-demo-pw" },
];

export default function LoginForm() {
  const { login, error } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const doLogin = async (user, pass) => {
    setSubmitting(true);
    try {
      await login(user, pass);
    } catch {
      // error is already surfaced via useAuth().error
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    doLogin(username, password);
  };

  const quickLogin = (user) => {
    setUsername(user.username);
    setPassword(user.password);
    doLogin(user.username, user.password);
  };

  return (
    <div className="panel">
      <h2>Log in</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button type="submit" disabled={submitting}>
          Log in
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="hint">Demo accounts, seeded by dice-user-service (Phase 2):</p>
      <div className="quick-logins">
        {DEMO_USERS.map((user) => (
          <button key={user.username} onClick={() => quickLogin(user)} disabled={submitting}>
            {user.username}
          </button>
        ))}
      </div>
    </div>
  );
}
