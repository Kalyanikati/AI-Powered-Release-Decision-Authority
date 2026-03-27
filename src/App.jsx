import { useMemo, useState } from "react";

const sampleTranscript = `Speaker 1: We should probably launch soon.
Speaker 2: Rahul will finalize deployment by March 30.
Speaker 3: Maybe Priya owns QA, not sure.
Speaker 2: Actually QA owner is Amit.`;

function normalizeList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  return [value];
}

function getScore(result) {
  if (!result || typeof result !== "object") return null;
  if (typeof result.score === "number") return result.score;
  if (typeof result.decision_integrity_score === "number")
    return result.decision_integrity_score;
  if (result.score && typeof result.score.value === "number")
    return result.score.value;
  return null;
}

export default function App() {
  const [apiUrl, setApiUrl] = useState("http://localhost:8000/analyze");
  const [transcript, setTranscript] = useState(sampleTranscript);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const score = useMemo(() => getScore(result), [result]);
  const decisions = useMemo(() => normalizeList(result?.decisions), [result]);
  const ambiguities = useMemo(
    () => normalizeList(result?.ambiguities || result?.ambiguity_flags),
    [result],
  );
  const conflicts = useMemo(() => normalizeList(result?.conflicts), [result]);

  async function onAnalyze(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(apiUrl.trim(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript }),
      });

      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        throw new Error(
          `Backend returned non-JSON response: ${text.slice(0, 250)}`,
        );
      }

      if (!response.ok) {
        const backendMsg = data?.detail || data?.message || response.statusText;
        throw new Error(`Request failed (${response.status}): ${backendMsg}`);
      }

      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong while calling the API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="bg-orb orb-a" />
      <div className="bg-orb orb-b" />

      <main className="container">
        <header className="hero">
          <p className="badge">ET GenAI Hackathon Prototype</p>
          <h1>Multilingual Decision Integrity Engine</h1>
          <p>
            Analyze meeting transcripts for decision clarity, ambiguity,
            conflict, and execution risk.
          </p>
        </header>

        <section className="panel">
          <form onSubmit={onAnalyze}>
            <label className="label">Backend API URL</label>
            <input
              className="input"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:8000/analyze"
              required
            />

            <label className="label">Transcript Input</label>
            <textarea
              className="textarea"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Paste transcript here..."
              required
            />

            <div className="actions">
              <button className="btn" type="submit" disabled={loading}>
                {loading ? "Analyzing..." : "Analyze Transcript"}
              </button>
            </div>
          </form>
        </section>

        {error && (
          <section className="panel error">
            <h3>Error</h3>
            <p>{error}</p>
          </section>
        )}

        {result && (
          <>
            <section className="grid">
              <article className="card score">
                <h3>Decision Integrity Score</h3>
                <p className="score-value">
                  {score !== null ? `${score}/100` : "Not provided"}
                </p>
              </article>

              <article className="card">
                <h3>Decisions</h3>
                <p className="count">{decisions.length}</p>
              </article>

              <article className="card">
                <h3>Ambiguities</h3>
                <p className="count">{ambiguities.length}</p>
              </article>

              <article className="card">
                <h3>Conflicts</h3>
                <p className="count">{conflicts.length}</p>
              </article>
            </section>

            <section className="panel">
              <h3>Friendly Summary</h3>

              <div className="list-block">
                <h4>Decisions</h4>
                {decisions.length === 0 ? (
                  <p className="muted">No decisions returned.</p>
                ) : (
                  <ul>
                    {decisions.map((item, i) => (
                      <li key={`d-${i}`}>
                        {typeof item === "string" ? item : JSON.stringify(item)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="list-block">
                <h4>Ambiguity Flags</h4>
                {ambiguities.length === 0 ? (
                  <p className="muted">No ambiguity flags returned.</p>
                ) : (
                  <ul>
                    {ambiguities.map((item, i) => (
                      <li key={`a-${i}`}>
                        {typeof item === "string" ? item : JSON.stringify(item)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="list-block">
                <h4>Conflicts</h4>
                {conflicts.length === 0 ? (
                  <p className="muted">No conflicts returned.</p>
                ) : (
                  <ul>
                    {conflicts.map((item, i) => (
                      <li key={`c-${i}`}>
                        {typeof item === "string" ? item : JSON.stringify(item)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>

            <section className="panel">
              <h3>Raw JSON Response</h3>
              <pre className="json">{JSON.stringify(result, null, 2)}</pre>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
