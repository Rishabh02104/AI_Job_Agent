"use client";

import { useEffect, useState } from "react";
import { 
  Play, 
  Briefcase, 
  CheckSquare, 
  FileCheck, 
  Mail, 
  Activity, 
  AlertCircle,
  Loader2
} from "lucide-react";

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [keywords, setKeywords] = useState("AI Engineer");
  const [limit, setLimit] = useState(5);
  const [message, setMessage] = useState("");

  const fetchStats = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/stats");
      if (!res.ok) {
        throw new Error(`API returned status ${res.status}`);
      }
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Error fetching stats:", err);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchStats();
  }, []);

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setMessage("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/pipeline/run?keywords=${encodeURIComponent(keywords)}&limit=${limit}`, {
        method: "POST"
      });
      const data = await res.json();
      if (data.success) {
        setMessage("E2E Job Agent pipeline started in background! Check back in a few seconds.");
      } else {
        setMessage("Failed to start pipeline: " + data.message);
      }
    } catch (err) {
      setMessage("Connection error. Is FastAPI running?");
    } finally {
      setRunning(false);
      // Refresh statistics
      setTimeout(fetchStats, 5000);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const appCounts = stats?.application_counts || {};
  const activeApps = (appCounts.reviewing || 0) + (appCounts.applied || 0) + (appCounts.interview || 0);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Agent Workspace</h1>
          <p className="text-slate-400 mt-1">Monitor, adjust, and review your autonomous career search pipeline.</p>
        </div>
        
        {/* Active Status Badge */}
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-full w-fit">
          <span className="flex h-3 w-3 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <span className="text-sm font-semibold text-slate-300">System Standby</span>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Card 1: Scouted */}
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden transition-all duration-200 hover:-translate-y-1">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-slate-400">Total Jobs Scouted</p>
              <h3 className="text-3xl font-bold mt-2">{stats?.jobs_found || 0}</h3>
            </div>
            <div className="p-3 bg-blue-500/10 text-blue-500 rounded-xl">
              <Briefcase className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4 text-xs text-blue-400 flex items-center space-x-1">
            <span>Aggregated from Internshala & Adzuna</span>
          </div>
        </div>

        {/* Card 2: Queued */}
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden transition-all duration-200 hover:-translate-y-1">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-slate-400">Queued for Review</p>
              <h3 className="text-3xl font-bold mt-2">{appCounts.reviewing || 0}</h3>
            </div>
            <div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-xl">
              <CheckSquare className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4 text-xs text-indigo-400 flex items-center space-x-1">
            <span>Staged at Human Gate</span>
          </div>
        </div>

        {/* Card 3: Applied */}
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden transition-all duration-200 hover:-translate-y-1">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-slate-400">Applications Sent</p>
              <h3 className="text-3xl font-bold mt-2">{appCounts.applied || 0}</h3>
            </div>
            <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-xl">
              <FileCheck className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4 text-xs text-emerald-400 flex items-center space-x-1">
            <span>Completed submissions</span>
          </div>
        </div>

        {/* Card 4: Interviews */}
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden transition-all duration-200 hover:-translate-y-1">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-slate-400">Interviews Scheduled</p>
              <h3 className="text-3xl font-bold mt-2">{appCounts.interview || 0}</h3>
            </div>
            <div className="p-3 bg-pink-500/10 text-pink-500 rounded-xl">
              <Mail className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4 text-xs text-pink-400 flex items-center space-x-1">
            <span>Gmail tracker notifications</span>
          </div>
        </div>
      </div>

      {/* Main Content Layout (Orchestration Panel & Score Distribution) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Orchestrator Trigger Panel */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-4 border-b border-slate-800">
              <Activity className="h-5 w-5 text-indigo-500" />
              <h3 className="text-lg font-bold">Pipeline Control Panel</h3>
            </div>
            <p className="text-sm text-slate-400 my-4">
              Trigger the Scout and Scorer pipeline to discover new job listings. 
              High compatibility matches (scoring 80%+) will be prepared automatically with tailored resume/CL drafts.
            </p>

            <form onSubmit={handleRunPipeline} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Search Keywords</label>
                <input 
                  type="text" 
                  value={keywords} 
                  onChange={(e) => setKeywords(e.target.value)} 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition" 
                  placeholder="e.g. AI Engineer, Backend Developer"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Maximum Scopes per Source</label>
                <select 
                  value={limit} 
                  onChange={(e) => setLimit(Number(e.target.value))} 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition"
                >
                  <option value={3}>3 Results</option>
                  <option value={5}>5 Results</option>
                  <option value={10}>10 Results</option>
                  <option value={15}>15 Results</option>
                </select>
              </div>

              <button 
                type="submit" 
                disabled={running}
                className="w-full flex items-center justify-center space-x-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition disabled:bg-indigo-800 disabled:text-slate-400 cursor-pointer"
              >
                {running ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Executing Pipeline Agents...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5 fill-current" />
                    <span>Trigger Scout & Match Pipeline</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {message && (
            <div className="mt-4 p-4 bg-slate-950 border border-slate-800 rounded-xl flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 text-indigo-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-slate-300">{message}</p>
            </div>
          )}
        </div>

        {/* Scoring Distribution Visualization */}
        <div className="glass-card rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-4 border-b border-slate-800">
              <Activity className="h-5 w-5 text-blue-500" />
              <h3 className="text-lg font-bold">Match Score Distribution</h3>
            </div>
            <p className="text-sm text-slate-400 my-4">
              Distribution of semantic compatibility scores computed across crawled job descriptions.
            </p>
            
            <div className="space-y-6 mt-6">
              {/* High Fit */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Strong Matches (≥ 80%)</span>
                  <span className="font-bold text-emerald-400">{stats?.match_distribution?.high || 0}</span>
                </div>
                <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden">
                  <div 
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${(stats?.match_distribution?.high / (stats?.jobs_found || 1)) * 100}%` }}
                  ></div>
                </div>
              </div>

              {/* Medium Fit */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Potential Fits (50% - 79%)</span>
                  <span className="font-bold text-blue-400">{stats?.match_distribution?.medium || 0}</span>
                </div>
                <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${(stats?.match_distribution?.medium / (stats?.jobs_found || 1)) * 100}%` }}
                  ></div>
                </div>
              </div>

              {/* Low Fit */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Low Matches (&lt; 50%)</span>
                  <span className="font-bold text-slate-400">{stats?.match_distribution?.low || 0}</span>
                </div>
                <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden">
                  <div 
                    className="bg-slate-700 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${(stats?.match_distribution?.low / (stats?.jobs_found || 1)) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <div className="text-xs text-slate-500 pt-4 border-t border-slate-800/60 mt-6">
            Scoring evaluates local all-MiniLM-L6-v2 embeddings + LLM fine-tuning adjustments.
          </div>
        </div>

      </div>
    </div>
  );
}
