"use client";

import { useEffect, useState } from "react";
import { 
  Inbox, 
  Check, 
  X, 
  FileText, 
  Download, 
  Briefcase, 
  AlertCircle,
  Loader2,
  Edit2,
  Save
} from "lucide-react";
import { API_BASE_URL } from "@/config";

export default function ReviewQueue() {
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAppIndex, setSelectedAppIndex] = useState<number>(0);
  const [coverLetter, setCoverLetter] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchApplications = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/applications`);
      if (!res.ok) {
        throw new Error(`API returned status ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        // Filter strictly for reviewing stage
        const reviewingApps = data.filter((a: any) => a.status === "reviewing");
        setApps(reviewingApps);
        
        if (reviewingApps.length > 0) {
          setCoverLetter(reviewingApps[0].cover_letter || "");
        }
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

  const handleSelectApp = (index: number) => {
    setSelectedAppIndex(index);
    setCoverLetter(apps[index].cover_letter || "");
  };

  const handleSaveCoverLetter = async () => {
    const activeApp = apps[selectedAppIndex];
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/applications/${activeApp.job_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cover_letter: coverLetter })
      });
      const data = await res.json();
      if (data.success) {
        // Update local copy
        const updatedApps = [...apps];
        updatedApps[selectedAppIndex].cover_letter = coverLetter;
        setApps(updatedApps);
        alert("Cover letter saved successfully!");
      }
    } catch (err) {
      alert("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    const activeApp = apps[selectedAppIndex];
    try {
      // Auto-save active changes first
      await fetch(`${API_BASE_URL}/api/applications/${activeApp.job_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cover_letter: coverLetter })
      });

      // Trigger Approve
      const res = await fetch(`${API_BASE_URL}/api/applications/${activeApp.job_id}/approve`, {
        method: "POST"
      });
      const data = await res.json();
      if (data.success) {
        alert("Application approved and marked as applied!");
        // Reload list
        const nextIndex = selectedAppIndex > 0 ? selectedAppIndex - 1 : 0;
        fetchApplications().then(() => {
          setSelectedAppIndex(nextIndex);
        });
      }
    } catch (err) {
      alert("Failed to approve application.");
    }
  };

  const handleReject = async () => {
    const activeApp = apps[selectedAppIndex];
    if (!confirm("Are you sure you want to reject and archive this application draft?")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/applications/${activeApp.job_id}/reject`, {
        method: "POST"
      });
      const data = await res.json();
      if (data.success) {
        alert("Application draft rejected and archived.");
        const nextIndex = selectedAppIndex > 0 ? selectedAppIndex - 1 : 0;
        fetchApplications().then(() => {
          setSelectedAppIndex(nextIndex);
        });
      }
    } catch (err) {
      alert("Failed to reject application.");
    }
  };

  if (loading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const activeApp = apps[selectedAppIndex];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Header Banner */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Review Queue</h1>
        <p className="text-slate-400 mt-1">Review, refine, and approve auto-tailored application drafts before submission.</p>
      </div>

      {apps.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/40 border border-slate-800 rounded-2xl">
          <Inbox className="h-16 w-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-bold">Queue is Empty</h3>
          <p className="text-slate-400 mt-1">There are no applications staged for human review. Run the pipeline to find matches!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* Left Navigation: List of staged apps */}
          <div className="lg:col-span-1 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Pending Applications ({apps.length})</h3>
            <div className="space-y-2 max-h-[65vh] overflow-y-auto pr-2">
              {apps.map((app, index) => {
                const isSelected = index === selectedAppIndex;
                return (
                  <div
                    key={app.id}
                    onClick={() => handleSelectApp(index)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                      isSelected 
                        ? "bg-slate-900 border-indigo-500/40 text-white shadow-md shadow-indigo-950/20" 
                        : "bg-slate-900/40 border-slate-850 text-slate-400 hover:border-slate-800 hover:text-slate-200"
                    }`}
                  >
                    <h4 className="font-bold text-sm truncate">{app.job?.title}</h4>
                    <p className="text-xs font-medium truncate mt-1">{app.job?.company}</p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs font-bold text-indigo-400">{app.score ? `${Math.round(app.score * 100)}% Match` : "N/A"}</span>
                      <span className="text-[10px] bg-slate-950 px-2 py-0.5 rounded border border-slate-850 uppercase tracking-wider text-slate-500">review</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Pane: Split screen view */}
          <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-8 glass-card border border-slate-850 rounded-2xl p-6 min-h-[60vh]">
            
            {/* Split Left: Job & Match Details */}
            <div className="space-y-6 flex flex-col justify-between border-b md:border-b-0 md:border-r border-slate-850 pb-6 md:pb-0 md:pr-6">
              <div className="space-y-6">
                <div>
                  <div className="flex items-center space-x-2 text-xs text-indigo-400 font-bold uppercase tracking-wider">
                    <Briefcase className="h-4 w-4" />
                    <span>Job Specifications</span>
                  </div>
                  <h2 className="text-2xl font-bold text-slate-100 mt-2">{activeApp.job?.title}</h2>
                  <p className="text-slate-400 font-semibold">{activeApp.job?.company} • {activeApp.job?.location}</p>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Scoring Fit</h4>
                  <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl">
                    <span className="text-xl font-extrabold text-emerald-400">{activeApp.score ? `${Math.round(activeApp.score * 100)}%` : "N/A"}</span>
                    <span className="text-xs text-slate-500 ml-2">Qualitative Alignment Score</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-bold">Original Job Listing</h4>
                  <p className="text-xs text-slate-400 bg-slate-950 border border-slate-850 p-4 rounded-xl max-h-52 overflow-y-auto whitespace-pre-line leading-relaxed">
                    {activeApp.job?.description}
                  </p>
                </div>
              </div>

              {/* Review Decision Buttons */}
              <div className="flex items-center gap-4 pt-4 border-t border-slate-850">
                <button
                  onClick={handleReject}
                  className="flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl border border-slate-800 bg-slate-900/40 hover:bg-pink-500/10 hover:border-pink-500/30 text-slate-400 hover:text-pink-400 transition font-semibold text-sm cursor-pointer"
                >
                  <X className="h-4 w-4" />
                  <span>Reject Application</span>
                </button>

                <button
                  onClick={handleApprove}
                  className="flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-lg shadow-indigo-950/40 cursor-pointer"
                >
                  <Check className="h-4 w-4" />
                  <span>Approve & Apply</span>
                </button>
              </div>
            </div>

            {/* Split Right: Tailored Resume & Cover Letter */}
            <div className="space-y-6 flex flex-col justify-between">
              
              <div className="space-y-6 flex-1 flex flex-col">
                <div>
                  <div className="flex items-center space-x-2 text-xs text-indigo-400 font-bold uppercase tracking-wider">
                    <FileText className="h-4 w-4" />
                    <span>Tailored Assets</span>
                  </div>
                  
                  {/* PDF Download link */}
                  {activeApp.tailored_resume_url && (
                    <div className="mt-4 p-4 bg-slate-950 border border-slate-850 rounded-xl flex items-center justify-between">
                      <div className="flex items-center space-x-2.5">
                        <FileText className="h-5 w-5 text-indigo-400" />
                        <div>
                          <p className="text-xs font-bold text-slate-200">Custom Resume PDF</p>
                          <p className="text-[10px] text-slate-500 mt-0.5 truncate max-w-[150px]">Generated via ReportLab</p>
                        </div>
                      </div>
                      <a 
                        href={activeApp.tailored_resume_url}
                        target="_blank" 
                        rel="noreferrer"
                        className="flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-semibold text-white transition cursor-pointer"
                      >
                        <Download className="h-3.5 w-3.5" />
                        <span>Download</span>
                      </a>
                    </div>
                  )}
                </div>

                {/* Cover Letter Editor */}
                <div className="space-y-2 flex-1 flex flex-col">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tailored Cover Letter Draft</label>
                    <button 
                      onClick={handleSaveCoverLetter}
                      disabled={saving}
                      className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition cursor-pointer"
                    >
                      {saving ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <>
                          <Save className="h-3.5 w-3.5" />
                          <span>Save Changes</span>
                        </>
                      )}
                    </button>
                  </div>
                  <textarea
                    value={coverLetter}
                    onChange={(e) => setCoverLetter(e.target.value)}
                    className="w-full flex-1 min-h-[300px] bg-slate-950 border border-slate-850 rounded-xl p-4 text-xs text-slate-300 leading-relaxed focus:outline-none focus:border-indigo-500 transition resize-none"
                    placeholder="Cover letter content..."
                  />
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
