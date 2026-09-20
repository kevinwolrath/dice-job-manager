import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth.jsx";
import { mcpApi } from "../api.js";

const SUGGESTIONS = [
  "What dice jobs do I have?",
  'Create a dice job called "Test batch" with 3 colours',
  "Show me Jane's dice jobs",
];

// This is the actual point of the whole project: a local model, talking to
// dice-mcp-server, whose tools (app/tools.py on the server) don't accept a
// user id at all — only whoever's token this tab is currently holding. Try
// asking things like "show me Jane's jobs" or "list jobs for user jane" —
// the model has no tool that could honor that even if it wanted to; the
// worst it can do is call get_my_jobs() again, which still only returns
// this tab's own user's jobs. That holds regardless of how the request is
// worded, which is the actual defense against prompt injection here: there
// is no parameter to inject into, not a filter that tries to catch bad
// wording.
//
// This used to be a small panel squeezed between the jobs list and the
// admin panel. It's now its own full-page view (see App.jsx's nav) so a
// real back-and-forth conversation — and the tool-call trace next to it —
// has room to breathe. The file is still named ChatPanel.jsx to avoid
// touching git history over a rename; what changed is the layout, not the
// underlying request/response logic.
export default function ChatPanel() {
  const { token, claims } = useAuth();
  const [history, setHistory] = useState([]); // [{role, content}] sent back to the server each turn
  const [turns, setTurns] = useState([]); // [{role, content, toolCalls?}] rendered in the UI
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns, loading]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    setInput("");
    setError(null);
    setTurns((t) => [...t, { role: "user", content: text }]);
    setLoading(true);
    try {
      const { reply, toolCalls } = await mcpApi.chat(token, text, history);
      setHistory((h) => [...h, { role: "user", content: text }, { role: "assistant", content: reply }]);
      setTurns((t) => [...t, { role: "assistant", content: reply, toolCalls }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleClear = () => {
    setHistory([]);
    setTurns([]);
    setError(null);
  };

  return (
    <div className="chat-page">
      <div className="chat-page-header">
        <div>
          <h2>Chat ({claims?.username})</h2>
          <p className="hint">
            Talks to dice-mcp-server, which runs tool calls against dice-ollama. Every tool is
            scoped to <strong>{claims?.username}</strong>'s own token, server-side — there is no
            tool parameter for "someone else's data" to land in, no matter how the request is
            worded. Try asking it to show or create a job for a different user by name.
          </p>
        </div>
        {turns.length > 0 && (
          <button type="button" className="chat-clear-btn" onClick={handleClear}>
            Clear conversation
          </button>
        )}
      </div>

      <div className="chat-page-turns" ref={scrollRef}>
        {turns.length === 0 && !loading && (
          <div className="chat-empty-state">
            <p>Ask about your dice jobs, or ask it to create one.</p>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button key={suggestion} type="button" onClick={() => sendMessage(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((turn, i) => (
          <div key={i} className={`chat-turn chat-turn-${turn.role}`}>
            <div className="chat-turn-role">{turn.role}</div>
            <div className="chat-turn-content">{turn.content}</div>
            {turn.toolCalls && turn.toolCalls.length > 0 && (
              <details className="chat-tool-trace">
                <summary>{turn.toolCalls.length} tool call(s)</summary>
                {turn.toolCalls.map((call, j) => (
                  <pre key={j}>
                    {call.name}({JSON.stringify(call.arguments)})
                    {"\n=> "}
                    {JSON.stringify(call.result, null, 2)}
                  </pre>
                ))}
              </details>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-turn chat-turn-assistant chat-turn-loading">
            <div className="chat-turn-role">assistant</div>
            <div className="chat-turn-content">thinking…</div>
          </div>
        )}
      </div>

      {error && <p className="error chat-page-error">{error}</p>}

      <form onSubmit={handleSubmit} className="chat-page-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. What dice jobs do I have?"
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
