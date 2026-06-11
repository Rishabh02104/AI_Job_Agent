"use client";

import { useEffect, useState } from "react";
import { 
  Briefcase, 
  ChevronDown, 
  ChevronUp, 
  CheckCircle2, 
  XCircle, 
  ExternalLink,
  ChevronRight,
  Plus,
  Loader2
} from "lucide-react";
import { API_BASE_URL } from "@/config";

export default function JobFeed() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoreFilter, setScoreFilter] = useState<number>(0);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [actioningJobId, setActioningJobId] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/jobs`);
      if (!res.ok) {
        throw new Error(`API returned status ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setJobs(data);
      } else {
        setJobs([]);
        console.error("Expected array for jobs, got:", data);
      }
    } catch (err) {
      console.error("Error fetching jobs:", err);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleStageJob = async (jobId: string) => {
    setActioningJobId(jobId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/applications/${jobId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "queued" })
      });
      const data = await res.json();
      if (data.success) {
        alert("Job successfully staged into queued status! The orchestrator will optimize assets on the next run.");
      }
    } catch (err) {
      alert("Failed to stage job.");
    } finally {
      setActioningJobId(null);
    }
  };

  const toggleExpand = (jobId: string) => {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
    } else {
      setExpandedJobId(jobId);
    }
  };

  const filteredJobs = Array.isArray(jobs) ? jobs.filter(job => {
    const score = job.match?.score || 0;
    return score >= scoreFilter;
  }) : [];


  if (loading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Scored Job Feed</h1>
          <p className="text-slate-400 mt-1">Semantic similarity evaluations of crawler listings against your resume.</p>
        </div>

        {/* Filter Sliders */}
        <div className="flex items-center space-x-3 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Min Score:</span>
          <select 
            value={scoreFilter} 
            onChange={(e) => setScoreFilter(Number(e.target.value))}
            className="bg-slate-950 border border-slate-850 rounded px-2 py-1 text-sm focus:outline-none text-slate-200"
          >
            <option value={0}>All Listings</option>
            <option value={0.5}>50%+ Fit</option>
            <option value={0.7}>70%+ Fit</option>
            <option value={0.8}>80%+ (Auto-queued)</option>
          </select>
        </div>
      </div>

      {/* Jobs Feed List */}
      <div className="space-y-4">
        {filteredJobs.length === 0 ? (
          <div className="text-center py-12 bg-slate-900/40 border border-slate-800 rounded-2xl">
            <Briefcase className="h-12 w-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No jobs found matching the active score thresholds.</p>
          </div>
        ) : (
          filteredJobs.map((job) => {
            const isExpanded = expandedJobId === job.id;
            const scorePercent = job.match?.score ? Math.round(job.match.score * 100) : null;
            const matchColor = scorePercent 
              ? scorePercent >= 80 
                ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" 
                : scorePercent >= 50 
                  ? "text-blue-400 border-blue-500/20 bg-blue-500/5" 
                  : "text-slate-400 border-slate-500/20 bg-slate-500/5"
              : "text-slate-500 border-slate-800 bg-slate-950";

            return (
              <div 
                key={job.id} 
                className={`glass-card rounded-2xl border transition-all duration-200 ${
                  isExpanded ? "border-indigo-500/40 ring-1 ring-indigo-500/10" : "border-slate-850 hover:border-slate-800"
                }`}
              >
                {/* Header card */}
                <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer" onClick={() => toggleExpand(job.id)}>
                  <div className="flex items-start space-x-4">
                    <div className="p-3 bg-slate-950 border border-slate-850 rounded-xl mt-1">
                      <Briefcase className="h-6 w-6 text-slate-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-100 hover:text-indigo-400 transition">{job.title}</h3>
                      <p className="text-sm text-slate-400 font-medium">{job.company} • {job.location || "Location N/A"}</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        <span className="text-xs bg-slate-950 border border-slate-850 px-2 py-0.5 rounded text-slate-400">{job.source}</span>
                      </div>
                    </div>
                  </div>

                  {/* Match score & Action buttons */}
                  <div className="flex items-center space-x-4 ml-auto md:ml-0">
                    <div className={`px-4 py-2 border rounded-xl flex flex-col items-center justify-center min-w-[80px] ${matchColor}`}>
                      <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Match</span>
                      <span className="text-lg font-bold">{scorePercent ? `${scorePercent}%` : "N/A"}</span>
                    </div>

                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStageJob(job.id);
                      }}
                      disabled={actioningJobId === job.id}
                      className="flex items-center space-x-1 px-4 py-2 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 hover:border-indigo-500/40 rounded-xl text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
                    >
                      {actioningJobId === job.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Plus className="h-4 w-4" />
                          <span>Queue App</span>
                        </>
                      )}
                    </button>

                    <div className="text-slate-500 hover:text-slate-300 transition">
                      {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Section */}
                {isExpanded && (
                  <div className="px-6 pb-6 border-t border-slate-850/60 pt-6 space-y-6 bg-slate-950/20 rounded-b-2xl">
                    {/* Skills assessment */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Matched skills */}
                      <div className="bg-slate-950/40 border border-slate-850 p-4 rounded-xl">
                        <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center mb-2">
                          <CheckCircle2 className="h-4 w-4 mr-1.5" />
                          <span>Matched Skills</span>
                        </h4>
                        {job.match?.matched_skills?.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {job.match.matched_skills.map((s: string) => (
                              <span key={s} className="text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2.5 py-1 rounded-lg">
                                {s}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500 mt-2">No overlapping skills matching the listing requirements.</p>
                        )}
                      </div>

                      {/* Missing skills */}
                      <div className="bg-slate-950/40 border border-slate-850 p-4 rounded-xl">
                        <h4 className="text-xs font-semibold text-pink-400 uppercase tracking-wider flex items-center mb-2">
                          <XCircle className="h-4 w-4 mr-1.5" />
                          <span>Missing Key Requirements</span>
                        </h4>
                        {job.match?.missing_skills?.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {job.match.missing_skills.map((s: string) => (
                              <span key={s} className="text-xs bg-pink-500/10 border border-pink-500/20 text-pink-400 px-2.5 py-1 rounded-lg">
                                {s}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500 mt-2">Resume addresses all major requirements detected in the post.</p>
                        )}
                      </div>
                    </div>

                    {/* Groq Match explanation */}
                    {job.match?.explanation && (
                      <div className="bg-slate-950/40 border border-slate-850 p-4 rounded-xl space-y-2">
                        <h4 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Agent Match Rationale</h4>
                        <p className="text-sm text-slate-300 leading-relaxed pt-1">{job.match.explanation}</p>
                      </div>
                    )}

                    {/* Job description */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Raw Job Description</h4>
                      <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-line bg-slate-950 border border-slate-850 p-4 rounded-xl max-h-60 overflow-y-auto">
                        {job.description}
                      </p>
                    </div>

                    {/* Redirect URL */}
                    <div className="pt-2">
                      <a 
                        href={job.url} 
                        target="_blank" 
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition"
                      >
                        <span>View Original Listing</span>
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
