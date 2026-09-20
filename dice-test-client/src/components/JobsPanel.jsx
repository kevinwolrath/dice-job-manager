import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../auth.jsx";
import { jobApi } from "../api.js";

export default function JobsPanel({ refreshKey }) {
  const { token } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setJobs(await jobApi.listMyJobs(token));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const handleDelete = async (id) => {
    setError(null);
    try {
      await jobApi.deleteJob(token, id);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="panel">
      <h2>My dice jobs</h2>
      <p className="hint">
        This list, and every action on it, is scoped to your own account by dice-job-service — there
        is no request this UI can make that reaches another user's jobs. Log in as a different demo
        user in another tab to see this list change to that user's own jobs.
      </p>
      {loading && <p>Loading…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && jobs.length === 0 && <p>No jobs yet — create one on the left.</p>}
      <ul className="jobs-list">
        {jobs.map((job) => (
          <li key={job.dice_job_id}>
            <div>
              <strong>{job.job_name}</strong> — {job.colour_count} colours
              <div className="job-id">{job.dice_job_id}</div>
            </div>
            <button onClick={() => handleDelete(job.dice_job_id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
