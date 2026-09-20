import { useAuth } from "../auth.jsx";

export default function UserBadge() {
  const { claims, logout } = useAuth();
  if (!claims) return null;
  return (
    <div className="user-badge">
      <span>
        Logged in as <strong>{claims.username}</strong> (role: {claims.role})
      </span>
      <button onClick={logout}>Log out</button>
    </div>
  );
}
