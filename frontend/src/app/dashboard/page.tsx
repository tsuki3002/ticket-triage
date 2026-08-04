"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { Ticket } from "@/types/ticket";

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-700",
  High: "bg-orange-100 text-orange-700",
  Medium: "bg-yellow-100 text-yellow-700",
  Low: "bg-gray-100 text-gray-600",
};

export default function DashboardPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadTickets();
  }, []);

  async function loadTickets(q?: string, status?: string) {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (q) params.q = q;
      if (status) params.status = status;
      const res = await api.get("/tickets", { params });
      setTickets(res.data);
    } catch {
      setError("Could not load tickets. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    loadTickets(search, statusFilter);
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_name");
    router.push("/login");
  }

  const counts = {
    open: tickets.filter((t) => t.status === "Open").length,
    assigned: tickets.filter((t) => t.status === "Assigned").length,
    inProgress: tickets.filter((t) => t.status === "In Progress").length,
    critical: tickets.filter((t) => t.priority === "Critical").length,
    resolved: tickets.filter((t) => t.status === "Resolved" || t.status === "Closed").length,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Ticket Triage Dashboard</h1>
        <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-800">
          Log out
        </button>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <CountCard label="Open" value={counts.open} />
          <CountCard label="Assigned" value={counts.assigned} />
          <CountCard label="In Progress" value={counts.inProgress} />
          <CountCard label="Critical" value={counts.critical} accent="text-red-600" />
          <CountCard label="Resolved" value={counts.resolved} />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search subject, customer, description..."
              className="border rounded px-3 py-2 text-sm w-72 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="">All statuses</option>
              <option value="Open">Open</option>
              <option value="Assigned">Assigned</option>
              <option value="In Progress">In Progress</option>
              <option value="Waiting for Customer">Waiting for Customer</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
            </select>
            <button type="submit" className="bg-gray-800 text-white text-sm rounded px-4 py-2 hover:bg-gray-900">
              Filter
            </button>
          </form>

          <button
            onClick={() => router.push("/tickets/new")}
            className="bg-blue-600 text-white text-sm font-medium rounded px-4 py-2 hover:bg-blue-700"
          >
            + Create Ticket
          </button>
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <p className="p-6 text-sm text-gray-500">Loading tickets...</p>
          ) : error ? (
            <p className="p-6 text-sm text-red-600">{error}</p>
          ) : tickets.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">No tickets found.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => router.push(`/tickets/${t.id}`)}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-4 py-3">#{t.id}</td>
                    <td className="px-4 py-3 max-w-xs truncate">{t.subject}</td>
                    <td className="px-4 py-3">{t.customer_name}</td>
                    <td className="px-4 py-3">{t.category || "—"}</td>
                    <td className="px-4 py-3">
                      {t.priority ? (
                        <span className={`px-2 py-1 rounded text-xs font-medium ${PRIORITY_COLORS[t.priority] || "bg-gray-100 text-gray-600"}`}>
                          {t.priority}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3">{t.status}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(t.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}

function CountCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-2xl font-semibold ${accent || "text-gray-900"}`}>{value}</p>
    </div>
  );
}