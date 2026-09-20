import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../auth.jsx";

// One small generic list+create+delete widget, reused for each admin-only
// reference-data entity below, instead of three near-identical components.
export default function EntityManager({ title, list, create, remove, idKey, labelKey }) {
  const { token } = useAuth();
  const [items, setItems] = useState([]);
  const [newLabel, setNewLabel] = useState("");
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setItems(await list(token));
    } catch (err) {
      setError(err.message);
    }
  }, [list, token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await create(token, newLabel);
      setNewLabel("");
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    setError(null);
    try {
      await remove(token, id);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="entity-manager">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item[idKey]}>
            {item[labelKey]}
            <button onClick={() => handleDelete(item[idKey])}>Delete</button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleCreate}>
        <input
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          placeholder={`New ${title.toLowerCase()}`}
          required
        />
        <button type="submit">Add</button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
