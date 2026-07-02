"use client";

import { useEffect, useState } from "react";
import { 
  ChevronRight, 
  MapPin, 
  Calendar, 
  ExternalLink,
  Loader2,
  Trash2
} from "lucide-react";
import { API_BASE_URL } from "@/config";

const COLUMNS = [
  { key: "saved", title: "Saved Listings", color: "border-slate-800 bg-slate-900/10 text-slate-400" },
  { key: "review_needed", title: "Review Needed", color: "border-amber-500/20 bg-amber-500/5 text-amber-400" },
  { key: "needs_human", title: "Action Required", color: "border-red-500/20 bg-red-500/5 text-red-400" },
  { key: "applied", title: "Applied", color: "border-blue-500/20 bg-blue-500/5 text-blue-400" },
  { key: "interview", title: "Interviews", color: "border-indigo-500/20 bg-indigo-500/5 text-indigo-400" },
  { key: "offer", title: "Offers", color: "border-emerald-500/20 bg-emerald-500/5 text-emerald-400" },
  { key: "rejected", title: "Archived", color: "border-pink-500/20 bg-pink-500/5 text-pink-400" }
];

export default function ApplicationTracker() {
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchApplications = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/applications`);
      if (!res.ok) {
        throw new Error(`API returned status ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setApps(data);
      } else {
        setApps([]);
        console.error("Expected array for applications, got:", data);
      }
    } catch (err) {
      console.error("Error fetching applications:", err);
      setApps([]);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchApplications();
  }, []);

  const handleStatusChange = async (jobId: string, newStatus: string) => {
    setUpdatingId(jobId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/applications/${jobId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      const data = await res.json();
      if (data.success) {
        // Refresh local applications
        fetchApplications();
      }
    } catch (err) {
      alert("Failed to update status.");
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-300 h-full flex flex-col">
      {/* Header Banner */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Application Tracker</h1>
        <p className="text-slate-400 mt-1">Organize and follow up on active application phases across Kanban lanes.</p>
      </div>

      {/* Kanban Board Layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 min-h-[60vh] overflow-x-auto pb-6">
        {COLUMNS.map((col) => {
          const colApps = Array.isArray(apps) ? apps.filter((app) => app.status === col.key) : [];


          return (
            <div key={col.key} className="flex flex-col bg-slate-900/20 border border-slate-850 rounded-2xl p-4 min-w-[240px]">
              {/* Column Title */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-850 mb-4">
                <h3 className="text-sm font-bold text-slate-300">{col.title}</h3>
                <span className="text-xs bg-slate-950 px-2.5 py-0.5 rounded-full border border-slate-850 font-semibold text-slate-400">
                  {colApps.length}
                </span>
              </div>

              {/* Column cards */}
              <div className="flex-1 space-y-4 overflow-y-auto max-h-[60vh] pr-1">
                {colApps.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-500 border border-dashed border-slate-850 rounded-xl">
                    No items staged
                  </div>
                ) : (
                  colApps.map((app) => (
                    <div key={app.id} className="p-4 bg-slate-900 border border-slate-850 rounded-xl space-y-3 shadow shadow-slate-950/20 hover:border-slate-850 transition relative">
                      {updatingId === app.job_id && (
                        <div className="absolute inset-0 bg-slate-950/50 backdrop-blur-[1px] rounded-xl flex items-center justify-center">
                          <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />
                        </div>
                      )}
                      
                      <div>
                        <h4 className="font-bold text-xs text-slate-200 line-clamp-1">{app.job?.title}</h4>
                        <p className="text-[10px] text-slate-400 truncate mt-0.5">{app.job?.company}</p>
                      </div>

                      {/* Score and source */}
                      <div className="flex justify-between items-center text-[10px] text-slate-500">
                        <span className="font-bold text-indigo-400">{app.score ? `${Math.round(app.score * 100)}% Match` : ""}</span>
                        <a 
                          href={app.job?.url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="hover:text-slate-300 flex items-center space-x-0.5"
                        >
                          <span>Listing</span>
                          <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      </div>

                      {/* Dropdown status switcher */}
                      <div className="pt-2 border-t border-slate-850/60 flex items-center justify-between gap-2">
                        <span className="text-[9px] uppercase tracking-wider text-slate-500">Move:</span>
                        <select
                          value={app.status}
                          onChange={(e) => handleStatusChange(app.job_id, e.target.value)}
                          className="bg-slate-950 border border-slate-850 rounded px-1.5 py-0.5 text-[10px] focus:outline-none text-slate-300 font-semibold"
                        >
                          {COLUMNS.map((c) => (
                            <option key={c.key} value={c.key}>{c.title}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
