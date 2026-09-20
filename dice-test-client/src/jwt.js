// Client-side JWT decoding, for display purposes ONLY (showing the logged-in
// username/role in the header, and deciding whether to render the admin
// panel at all). This is never a security boundary — anyone can read or
// forge the payload of a JWT they hold without the private key, so nothing
// server-side ever trusts a claim just because the browser parsed it here.
// Every real check (who owns a job, who can write reference data) happens
// again, independently, inside the service that receives the request.
export function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}
