import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import { stockApi, jobApi } from "../api.js";

export default function CreateJobForm({ onCreated }) {
  const { token } = useAuth();
  const [materialTypes, setMaterialTypes] = useState([]);
  const [productionMethods, setProductionMethods] = useState([]);
  const [numberColours, setNumberColours] = useState([]);
  const [form, setForm] = useState({
    job_name: "",
    colour_count: 2,
    material_type_id: "",
    production_method_id: "",
    dice_job_number_colour_id: "",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadReferenceData() {
      try {
        // Any authenticated user can read this — it's shared reference
        // data, not owned by anyone (Phase 1). Only writing to it is
        // admin-gated.
        const [mt, pm, nc] = await Promise.all([
          stockApi.listMaterialTypes(token),
          stockApi.listProductionMethods(token),
          stockApi.listDiceJobNumberColours(token),
        ]);
        if (cancelled) return;
        setMaterialTypes(mt);
        setProductionMethods(pm);
        setNumberColours(nc);
        setForm((f) => ({
          ...f,
          material_type_id: mt[0]?.material_type_id ?? "",
          production_method_id: pm[0]?.production_method_id ?? "",
          dice_job_number_colour_id: nc[0]?.dice_job_number_colour_id ?? "",
        }));
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    loadReferenceData();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await jobApi.createJob(token, { ...form, colour_count: Number(form.colour_count) });
      setForm((f) => ({ ...f, job_name: "" }));
      onCreated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const referenceDataReady =
    materialTypes.length > 0 && productionMethods.length > 0 && numberColours.length > 0;

  if (!referenceDataReady) {
    return (
      <div className="panel">
        <h2>New dice job</h2>
        <p>
          Waiting on reference data from dice-stock-service. If nothing ever loads, make sure it's
          seeded — see the README's "Start Phase 1 locally" section.
        </p>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>New dice job</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Job name
          <input value={form.job_name} onChange={(e) => setForm({ ...form, job_name: e.target.value })} required />
        </label>
        <label>
          Colour count
          <input
            type="number"
            min="1"
            value={form.colour_count}
            onChange={(e) => setForm({ ...form, colour_count: e.target.value })}
            required
          />
        </label>
        <label>
          Material type
          <select
            value={form.material_type_id}
            onChange={(e) => setForm({ ...form, material_type_id: e.target.value })}
          >
            {materialTypes.map((mt) => (
              <option key={mt.material_type_id} value={mt.material_type_id}>
                {mt.description}
              </option>
            ))}
          </select>
        </label>
        <label>
          Production method
          <select
            value={form.production_method_id}
            onChange={(e) => setForm({ ...form, production_method_id: e.target.value })}
          >
            {productionMethods.map((pm) => (
              <option key={pm.production_method_id} value={pm.production_method_id}>
                {pm.description}
              </option>
            ))}
          </select>
        </label>
        <label>
          Job number colour
          <select
            value={form.dice_job_number_colour_id}
            onChange={(e) => setForm({ ...form, dice_job_number_colour_id: e.target.value })}
          >
            {numberColours.map((nc) => (
              <option key={nc.dice_job_number_colour_id} value={nc.dice_job_number_colour_id}>
                {nc.dice_job_number_colour_name}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={submitting}>
          Create job
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
