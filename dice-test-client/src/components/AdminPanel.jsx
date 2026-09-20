import { useAuth } from "../auth.jsx";
import EntityManager from "./EntityManager.jsx";
import { stockApi } from "../api.js";

export default function AdminPanel() {
  const { claims } = useAuth();

  // This check only decides what THIS UI renders — it is not the security
  // boundary, and never could be: claims come from a JWT this browser can
  // read (and, if it wanted to, forge a fake copy of) without needing the
  // private signing key. The real gate is server-side: every write below
  // still goes through dice-stock-service's own require_admin dependency,
  // which independently verifies the token's signature and role claim. Log
  // in as `john`, open this browser's dev tools, and try POSTing to
  // /material-types with john's real (unmodified) token to see the 403 come
  // back from the server regardless of what this component would have shown.
  if (claims?.role !== "admin") {
    return (
      <div className="panel">
        <h2>Admin</h2>
        <p>Only accounts with role "admin" can manage shared reference data. Log in as `admin` to see this panel.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Admin: shared reference data</h2>
      <p className="hint">
        These writes are gated by the `role` claim in your JWT — checked only inside
        dice-stock-service, nowhere else in this project (not dice-job-service, not this UI's own
        logic beyond hiding this panel). Admin never gets special access to anyone's jobs.
      </p>
      <EntityManager
        title="Material types"
        list={stockApi.listMaterialTypes}
        create={stockApi.createMaterialType}
        remove={stockApi.deleteMaterialType}
        idKey="material_type_id"
        labelKey="description"
      />
      <EntityManager
        title="Production methods"
        list={stockApi.listProductionMethods}
        create={stockApi.createProductionMethod}
        remove={stockApi.deleteProductionMethod}
        idKey="production_method_id"
        labelKey="description"
      />
      <EntityManager
        title="Dice job number colours"
        list={stockApi.listDiceJobNumberColours}
        create={stockApi.createDiceJobNumberColour}
        remove={stockApi.deleteDiceJobNumberColour}
        idKey="dice_job_number_colour_id"
        labelKey="dice_job_number_colour_name"
      />
      <p className="hint">
        Colour types, colour brands, and material stock aren't wired up in this minimal panel — use
        the same admin token against dice-stock-service's other endpoints directly (see the README)
        if you need to manage those.
      </p>
    </div>
  );
}
