"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import api from "@/lib/api";
import { Ticket, Comment, Activity } from "@/types/ticket";

// Matches seed.py's TEAMS list order. There's no GET /teams endpoint yet,
// so this mirrors the seeded data -- documented as a known simplification.
const TEAMS = [
  { id: 1, name: "Platform Engineering" },
  { id: 2, name: "Application Engineering" },
  { id: 3, name: "Security" },
  { id: 4, name: "DevOps" },
  { id: 5, name: "Database Team" },
  { id: 6, name: "Billing Team" },
  { id: 7, name: "Customer Support" },
  { id: 8, name: "Product Team" },
];

const CATEGORIES = [
  "Authentication", "Billing", "Performance", "Data Issue", "Integration",
  "User Interface", "Access Request", "Feature Request", "Security",
  "General Support", "Unknown",
];

const PRIORITIES = ["Low", "Medium", "High", "Critical"];

const STATUSES = ["Open", "Assigned", "In Progress", "Waiting for Customer", "Resolved", "Closed"];

export default function TicketDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const ticketId = params.id as string;

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Editable AI-suggestion fields
  const [summary, setSummary] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("");
  const [recommendedTeam, setRecommendedTeam] = useState("");
  const [suggestedResponse, setSuggestedResponse] = useState("");

  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [savingReview, setSavingReview] = useState(false);

  const [assignTeamId, setAssignTeamId] = useState("");
  const [assigning, setAssigning] = useState(false);

  const [statusValue, setStatusValue] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const [newComment, setNewComment] = useState("");
  const [postingComment, setPostingComment] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadAll();
  }, [ticketId]);

  async function loadAll() {
    setLoading(true);
    setLoadError(null);
    try {
      const [ticketRes, commentsRes, activitiesRes] = await Promise.all([
        api.get(`/tickets/${ticketId}`),
        api.get(`/tickets/${ticketId}/comments`),
        api.get(`/tickets/${ticketId}/activities`),
      ]);
      applyTicket(ticketRes.data);
      setComments(commentsRes.data);
      setActivities(activitiesRes.data);
    } catch {
      setLoadError("Could not load this ticket.");
    } finally {
      setLoading(false);
    }
  }

  function applyTicket(t: Ticket) {
    setTicket(t);
    setSummary(t.summary || "");
    setCategory(t.category || "");
    setPriority(t.priority || "");
    setRecommendedTeam(t.recommended_team || "");
    setSuggestedResponse(t.suggested_response || "");
    setStatusValue(t.status);
    setAssignTeamId(t.assigned_team_id ? String(t.assigned_team_id) : "");
  }

  async function handleAnalyze() {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const res = await api.post(`/tickets/${ticketId}/analyze`);
      if (res.data.status === "failed") {
        setAnalyzeError(res.data.error || "AI analysis failed. You can retry.");
      } else {
        applyTicket(res.data.ticket);
      }
      const activitiesRes = await api.get(`/tickets/${ticketId}/activities`);
      setActivities(activitiesRes.data);
    } catch {
      setAnalyzeError("AI analysis failed. You can retry.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSaveReview() {
    setSavingReview(true);
    try {
      const res = await api.put(`/tickets/${ticketId}`, {
        summary, category, priority,
        recommended_team: recommendedTeam,
        suggested_response: suggestedResponse,
      });
      applyTicket(res.data);
      const activitiesRes = await api.get(`/tickets/${ticketId}/activities`);
      setActivities(activitiesRes.data);
    } catch {
      alert("Could not save changes.");
    } finally {
      setSavingReview(false);
    }
  }

  async function handleAssign() {
    if (!assignTeamId) return;
    setAssigning(true);
    try {
      const res = await api.put(`/tickets/${ticketId}/assignment`, { team_id: Number(assignTeamId) });
      applyTicket(res.data);
      const activitiesRes = await api.get(`/tickets/${ticketId}/activities`);
      setActivities(activitiesRes.data);
    } catch {
      alert("Could not assign ticket. Team may not exist -- check that seed.py has been run.");
    } finally {
      setAssigning(false);
    }
  }

  async function handleStatusUpdate() {
    if (!statusValue || !ticket) return;
    setUpdatingStatus(true);
    try {
      const res = await api.put(`/tickets/${ticketId}/status`, { status: statusValue });
      applyTicket(res.data);
      const activitiesRes = await api.get(`/tickets/${ticketId}/activities`);
      setActivities(activitiesRes.data);
    } catch {
      alert("Could not update status.");
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    if (!newComment.trim()) return;
    setPostingComment(true);
    try {
      await api.post(`/tickets/${ticketId}/comments`, { text: newComment.trim() });
      setNewComment("");
      const [commentsRes, activitiesRes] = await Promise.all([
        api.get(`/tickets/${ticketId}/comments`),
        api.get(`/tickets/${ticketId}/activities`),
      ]);
      setComments(commentsRes.data);
      setActivities(activitiesRes.data);
    } catch {
      alert("Could not add comment.");
    } finally {
      setPostingComment(false);
    }
  }

  if (loading) return <div className="p-8 text-sm text-gray-500">Loading ticket...</div>;
  if (loadError || !ticket) return <div className="p-8 text-sm text-red-600">{loadError || "Ticket not found."}</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <button onClick={() => router.push("/dashboard")} className="text-sm text-gray-500 hover:text-gray-800 mb-1">
            ← Back to dashboard
          </button>
          <h1 className="text-lg font-semibold">Ticket #{ticket.id}: {ticket.subject}</h1>
        </div>
        <span className="text-xs px-3 py-1 rounded-full bg-gray-100">{ticket.status}</span>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Original ticket info -- never modified by AI */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-semibold text-gray-500 mb-4">Original Ticket (customer-submitted)</h2>
          <dl className="grid grid-cols-2 gap-4 text-sm mb-4">
            <div><dt className="text-gray-500">Customer</dt><dd>{ticket.customer_name}</dd></div>
            <div><dt className="text-gray-500">Email</dt><dd>{ticket.customer_email}</dd></div>
            <div><dt className="text-gray-500">Product/Module</dt><dd>{ticket.product_module || "—"}</dd></div>
            <div><dt className="text-gray-500">Attachment</dt><dd>{ticket.attachment_link || "—"}</dd></div>
          </dl>
          <div>
            <p className="text-gray-500 text-sm mb-1">Description</p>
            <p className="text-sm whitespace-pre-wrap bg-gray-50 rounded p-3">{ticket.description}</p>
          </div>
        </section>

        {/* AI suggestions -- editable */}
        <section className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-500">
              AI Suggestions <span className="font-normal text-gray-400">(suggestion only — review before use)</span>
            </h2>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="text-sm bg-blue-600 text-white rounded px-3 py-1.5 hover:bg-blue-700 disabled:opacity-50"
            >
              {analyzing ? "Analyzing..." : ticket.summary ? "Retry AI Analysis" : "Run AI Analysis"}
            </button>
          </div>

          {analyzeError && (
            <p className="text-sm text-red-600 mb-4">
              {analyzeError} — the ticket itself is safe and unaffected.
            </p>
          )}

          {!ticket.summary && !analyzeError ? (
            <p className="text-sm text-gray-400">No AI analysis yet. Click "Run AI Analysis" above.</p>
          ) : (
            <div className="space-y-4">
              <Field label="Summary">
                <textarea value={summary} onChange={(e) => setSummary(e.target.value)} rows={2} className="w-full border rounded px-3 py-2 text-sm" />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Category">
                  <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
                <Field label="Priority">
                  <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                    {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </Field>
              </div>
              <Field label="Recommended Team (AI suggestion, free text)">
                <input value={recommendedTeam} onChange={(e) => setRecommendedTeam(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
              </Field>
              <Field label="Suggested Response">
                <textarea value={suggestedResponse} onChange={(e) => setSuggestedResponse(e.target.value)} rows={3} className="w-full border rounded px-3 py-2 text-sm" />
              </Field>
              <button
                onClick={handleSaveReview}
                disabled={savingReview}
                className="bg-gray-800 text-white text-sm rounded px-4 py-2 hover:bg-gray-900 disabled:opacity-50"
              >
                {savingReview ? "Saving..." : "Save Reviewed Values"}
              </button>
            </div>
          )}
        </section>

        {/* Assignment + status */}
        <section className="bg-white rounded-lg shadow p-6 grid grid-cols-2 gap-6">
          <div>
            <h2 className="text-sm font-semibold text-gray-500 mb-3">Assignment</h2>
            <select value={assignTeamId} onChange={(e) => setAssignTeamId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm mb-2">
              <option value="">Select a team...</option>
              {TEAMS.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <button onClick={handleAssign} disabled={assigning || !assignTeamId} className="text-sm bg-gray-800 text-white rounded px-4 py-2 hover:bg-gray-900 disabled:opacity-50">
              {assigning ? "Assigning..." : "Assign Team"}
            </button>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-gray-500 mb-3">Status</h2>
            <select value={statusValue} onChange={(e) => setStatusValue(e.target.value)} className="w-full border rounded px-3 py-2 text-sm mb-2">
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button onClick={handleStatusUpdate} disabled={updatingStatus} className="text-sm bg-gray-800 text-white rounded px-4 py-2 hover:bg-gray-900 disabled:opacity-50">
              {updatingStatus ? "Updating..." : "Update Status"}
            </button>
          </div>
        </section>

        {/* Comments */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-semibold text-gray-500 mb-3">Internal Comments</h2>
          <div className="space-y-3 mb-4">
            {comments.length === 0 && <p className="text-sm text-gray-400">No comments yet.</p>}
            {comments.map((c) => (
              <div key={c.id} className="text-sm bg-gray-50 rounded p-3">
                <p>{c.text}</p>
                <p className="text-xs text-gray-400 mt-1">{new Date(c.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
          <form onSubmit={handleAddComment} className="flex gap-2">
            <input
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Add an internal comment..."
              className="flex-1 border rounded px-3 py-2 text-sm"
            />
            <button type="submit" disabled={postingComment} className="bg-blue-600 text-white text-sm rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50">
              {postingComment ? "Posting..." : "Post"}
            </button>
          </form>
        </section>

        {/* Activity timeline */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-semibold text-gray-500 mb-3">Activity Timeline</h2>
          <ul className="space-y-2">
            {activities.map((a) => (
              <li key={a.id} className="text-sm flex justify-between border-b last:border-0 py-2">
                <span>{a.description}</span>
                <span className="text-xs text-gray-400">{new Date(a.timestamp).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      {children}
    </div>
  );
}