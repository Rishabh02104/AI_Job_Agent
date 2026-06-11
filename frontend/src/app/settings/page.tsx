"use client";

import { useEffect, useState } from "react";
import { 
  Settings, 
  Upload, 
  FileText, 
  Save, 
  Loader2, 
  AlertCircle,
  Sliders,
  Mail,
  Lock,
  Calendar,
  Briefcase,
  Code,
  ExternalLink,
  Globe,
  UserCheck
} from "lucide-react";
import { API_BASE_URL } from "@/config";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"system" | "resume">("system");
  
  // Resume state
  const [resume, setResume] = useState<any>(null);
  const [resumeLoading, setResumeLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [savingResume, setSavingResume] = useState(false);
  const [resumeJsonStr, setResumeJsonStr] = useState("");
  const [resumeMessage, setResumeMessage] = useState("");

  // System Settings state
  const [settings, setSettings] = useState<any>({
    keywords: "AI Engineer",
    location: "",
    limit_count: 5,
    threshold: 0.8,
    internshala_email: "",
    internshala_password: "",
    gmail_email: "",
    gmail_app_password: "",
    schedule_interval_hours: 12,
    is_schedule_enabled: true,
    github_url: "",
    linkedin_url: "",
    portfolio_url: "",
    requires_sponsorship: false,
    authorized_to_work: true,
    notice_period_days: 0,
    salary_expectations: "",
    gender: "Decline to self-identify",
    race: "Decline to self-identify",
    disability_status: "Decline to self-identify",
    veteran_status: "Decline to self-identify"
  });
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState("");
  const [migrationPending, setMigrationPending] = useState(false);
  const [copilotMigrationPending, setCopilotMigrationPending] = useState(false);

  const fetchResume = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/resume`);
      if (res.ok) {
        const data = await res.json();
        if (data) {
          setResume(data);
          setResumeJsonStr(JSON.stringify(data.parsed_json, null, 2));
        }
      }
    } catch (err) {
      console.error("Error fetching resume:", err);
    } finally {
      setResumeLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        if (data.migration_pending) {
          setMigrationPending(true);
        } else {
          setMigrationPending(false);
        }
        if (data.copilot_migration_pending) {
          setCopilotMigrationPending(true);
        } else {
          setCopilotMigrationPending(false);
        }
      }
    } catch (err) {
      console.error("Error fetching settings:", err);
    } finally {
      setSettingsLoading(false);
    }
  };

  useEffect(() => {
    fetchResume();
    fetchSettings();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    setResumeMessage("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/resume/upload`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        throw new Error(`Upload failed with status ${res.status}`);
      }
      const data = await res.json();
      if (data.success) {
        setResumeMessage("Resume uploaded and parsed successfully!");
        fetchResume();
      } else {
        setResumeMessage("Failed to upload: " + data.detail);
      }
    } catch (err) {
      setResumeMessage("Upload connection error. Is FastAPI backend running?");
    } finally {
      setUploading(false);
    }
  };

  const handleSaveResumeJson = async () => {
    setSavingResume(true);
    setResumeMessage("");
    try {
      const parsedJson = JSON.parse(resumeJsonStr);
      const res = await fetch(`${API_BASE_URL}/api/resume`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsedJson)
      });
      if (!res.ok) {
        throw new Error(`Save failed with status ${res.status}`);
      }
      const data = await res.json();
      if (data.success) {
        setResumeMessage("Base resume structure saved successfully!");
        fetchResume();
      }
    } catch (err) {
      setResumeMessage("Invalid JSON formatting. Please check syntax before saving.");
    } finally {
      setSavingResume(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    setSettingsMessage("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        setSettingsMessage("System settings saved successfully!");
        if (data.migration_pending) {
          setMigrationPending(true);
        } else {
          setMigrationPending(false);
        }
        if (data.copilot_migration_pending) {
          setCopilotMigrationPending(true);
        } else {
          setCopilotMigrationPending(false);
        }
      } else {
        const errData = await res.json();
        setSettingsMessage("Failed to save settings: " + (errData.detail || "Error"));
      }
    } catch (err) {
      setSettingsMessage("Connection error. Is FastAPI backend running?");
    } finally {
      setSavingSettings(false);
    }
  };

  if (resumeLoading || settingsLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
      {/* Header Banner */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Configuration Hub</h1>
        <p className="text-slate-400 mt-1">Manage your automated search preferences, email alerts, credentials, and resume profiles.</p>
      </div>

      {/* Tabs Nav */}
      <div className="flex space-x-1 p-1 bg-slate-950 border border-slate-850 rounded-xl w-fit">
        <button
          onClick={() => setActiveTab("system")}
          className={`flex items-center space-x-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition cursor-pointer ${
            activeTab === "system"
              ? "bg-indigo-600 text-white shadow"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sliders className="h-4 w-4" />
          <span>System Configurations</span>
        </button>
        <button
          onClick={() => setActiveTab("resume")}
          className={`flex items-center space-x-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition cursor-pointer ${
            activeTab === "resume"
              ? "bg-indigo-600 text-white shadow"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>Resume Profile & JSON</span>
        </button>
      </div>

      {/* Tab 1: System Settings Form */}
      {activeTab === "system" && (
        <form onSubmit={handleSaveSettings} className="space-y-8 max-w-4xl">
          
          {migrationPending && (
            <div className="p-5 bg-pink-950/20 border border-pink-500/20 rounded-2xl flex items-start space-x-3.5">
              <AlertCircle className="h-6 w-6 text-pink-400 mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-pink-400">Database Migration Required</h4>
                <p className="text-xs text-slate-350 leading-relaxed">
                  The <code className="bg-slate-950 px-1 py-0.5 rounded text-[10px] text-pink-300">system_settings</code> table does not exist in your Supabase database. 
                  To enable settings saving, please copy the content of <span className="font-semibold text-slate-200">20260611000100_add_settings.sql</span> and run it inside the Supabase SQL Editor.
                </p>
              </div>
            </div>
          )}

          {copilotMigrationPending && (
            <div className="p-5 bg-amber-950/20 border border-amber-500/20 rounded-2xl flex items-start space-x-3.5">
              <AlertCircle className="h-6 w-6 text-amber-400 mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-amber-400">Copilot Schema Migration Required</h4>
                <p className="text-xs text-slate-350 leading-relaxed">
                  The Simplify Copilot fields (social links, demographics) do not exist in your database table. 
                  To enable auto-fill and profile saving, please copy the content of <span className="font-semibold text-slate-200">20260611000200_add_copilot_fields.sql</span> and execute it in your Supabase SQL Editor.
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Column Left: Job Scouting Parameters */}
            <div className="glass-card rounded-2xl p-6 space-y-6">
              <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
                <Briefcase className="h-5 w-5 text-indigo-500" />
                <h3 className="text-base font-bold">Search Parameters</h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Search Keywords</label>
                  <input
                    type="text"
                    value={settings.keywords || ""}
                    onChange={(e) => setSettings({ ...settings, keywords: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    placeholder="e.g. AI Engineer, React Developer"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Preferred Location</label>
                  <input
                    type="text"
                    value={settings.location || ""}
                    onChange={(e) => setSettings({ ...settings, location: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    placeholder="e.g. Remote, India, Bengaluru"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Daily Limits</label>
                    <select
                      value={settings.limit_count || 5}
                      onChange={(e) => setSettings({ ...settings, limit_count: Number(e.target.value) })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    >
                      <option value={3}>3 jobs</option>
                      <option value={5}>5 jobs</option>
                      <option value={10}>10 jobs</option>
                      <option value={20}>20 jobs</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Match Threshold</label>
                    <select
                      value={settings.threshold || 0.8}
                      onChange={(e) => setSettings({ ...settings, threshold: Number(e.target.value) })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    >
                      <option value={0.5}>50% Compatibility</option>
                      <option value={0.6}>60% Compatibility</option>
                      <option value={0.7}>70% Compatibility</option>
                      <option value={0.8}>80% (Auto-stage)</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* Column Right: Automated Scheduler Configuration */}
            <div className="glass-card rounded-2xl p-6 space-y-6">
              <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
                <Calendar className="h-5 w-5 text-indigo-500" />
                <h3 className="text-base font-bold">Auto-Scout Scheduler</h3>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-slate-950 border border-slate-850 rounded-xl">
                  <div>
                    <p className="text-xs font-bold text-slate-200">Enable Scout Schedules</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Scouts and scores listings in the background.</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.is_schedule_enabled || false}
                    onChange={(e) => setSettings({ ...settings, is_schedule_enabled: e.target.checked })}
                    className="h-4 w-4 accent-indigo-600 rounded cursor-pointer"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Check Interval (Hours)</label>
                  <input
                    type="number"
                    value={settings.schedule_interval_hours || 12}
                    onChange={(e) => setSettings({ ...settings, schedule_interval_hours: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    min={1}
                    max={168}
                    required
                  />
                </div>
              </div>
            </div>

          </div>

          {/* Credentials Settings Card */}
          <div className="glass-card rounded-2xl p-6 space-y-6">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Lock className="h-5 w-5 text-indigo-500" />
              <h3 className="text-base font-bold">Browser Submission & Email Tracker Credentials</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Internshala Credentials */}
              <div className="space-y-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-bold">Internshala Auto-Apply Credentials</h4>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Email address</label>
                  <input
                    type="email"
                    value={settings.internshala_email || ""}
                    onChange={(e) => setSettings({ ...settings, internshala_email: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                    placeholder="name@example.com"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Password</label>
                  <input
                    type="password"
                    value={settings.internshala_password || ""}
                    onChange={(e) => setSettings({ ...settings, internshala_password: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>

              {/* Gmail / IMAP credentials */}
              <div className="space-y-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-bold flex items-center">
                  <Mail className="h-3.5 w-3.5 mr-1" />
                  <span>Gmail IMAP & SMTP App Password</span>
                </h4>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Gmail Address</label>
                  <input
                    type="email"
                    value={settings.gmail_email || ""}
                    onChange={(e) => setSettings({ ...settings, gmail_email: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                    placeholder="username@gmail.com"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Gmail App Password (16 characters)</label>
                  <input
                    type="password"
                    value={settings.gmail_app_password || ""}
                    onChange={(e) => setSettings({ ...settings, gmail_app_password: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                    placeholder="abcd efgh ijkl mnop"
                  />
                  <span className="text-[9px] text-slate-500 block mt-1">Requires standard 2-Step Verification App Password from Google settings.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Simplify Copilot Profiles Card */}
          <div className="glass-card rounded-2xl p-6 space-y-6">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <UserCheck className="h-5 w-5 text-indigo-500" />
              <h3 className="text-base font-bold">Simplify Copilot & Profiles (Auto-fill Options)</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Social Links & Work Authorization */}
              <div className="space-y-6">
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-bold">Social Links & Websites</h4>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1 flex items-center">
                      <Code className="h-3 w-3 mr-1 text-slate-400" /> GitHub URL
                    </label>
                    <input
                      type="url"
                      value={settings.github_url || ""}
                      onChange={(e) => setSettings({ ...settings, github_url: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                      placeholder="https://github.com/username"
                      disabled={copilotMigrationPending}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1 flex items-center">
                      <ExternalLink className="h-3 w-3 mr-1 text-slate-400" /> LinkedIn URL
                    </label>
                    <input
                      type="url"
                      value={settings.linkedin_url || ""}
                      onChange={(e) => setSettings({ ...settings, linkedin_url: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                      placeholder="https://linkedin.com/in/username"
                      disabled={copilotMigrationPending}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1 flex items-center">
                      <Globe className="h-3 w-3 mr-1 text-slate-400" /> Portfolio Website
                    </label>
                    <input
                      type="url"
                      value={settings.portfolio_url || ""}
                      onChange={(e) => setSettings({ ...settings, portfolio_url: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                      placeholder="https://myportfolio.com"
                      disabled={copilotMigrationPending}
                    />
                  </div>
                </div>

                <div className="space-y-4 pt-4 border-t border-slate-900">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-bold">Work Authorization & Salary</h4>
                  <div className="flex items-center justify-between p-3 bg-slate-950 border border-slate-900 rounded-xl">
                    <div>
                      <p className="text-xs font-bold text-slate-200">Authorized to Work</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Are you legally authorized to work in the target country?</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.authorized_to_work ?? true}
                      onChange={(e) => setSettings({ ...settings, authorized_to_work: e.target.checked })}
                      className="h-4 w-4 accent-indigo-600 rounded cursor-pointer"
                      disabled={copilotMigrationPending}
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-slate-950 border border-slate-900 rounded-xl">
                    <div>
                      <p className="text-xs font-bold text-slate-200">Requires Sponsorship</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Will you now or in the future require visa sponsorship?</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.requires_sponsorship ?? false}
                      onChange={(e) => setSettings({ ...settings, requires_sponsorship: e.target.checked })}
                      className="h-4 w-4 accent-indigo-600 rounded cursor-pointer"
                      disabled={copilotMigrationPending}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] text-slate-500 mb-1">Notice Period (Days)</label>
                      <input
                        type="number"
                        value={settings.notice_period_days ?? 0}
                        onChange={(e) => setSettings({ ...settings, notice_period_days: Number(e.target.value) })}
                        className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                        min={0}
                        disabled={copilotMigrationPending}
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-500 mb-1">Salary Expectation</label>
                      <input
                        type="text"
                        value={settings.salary_expectations || ""}
                        onChange={(e) => setSettings({ ...settings, salary_expectations: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200 font-mono"
                        placeholder="e.g. $120,000 /yr"
                        disabled={copilotMigrationPending}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Legal Demographics (EEO) */}
              <div className="space-y-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-bold">Legal Demographics & Equal Opportunity (EEO)</h4>
                <p className="text-[10px] text-slate-500 leading-relaxed mb-4">
                  Greenhouse, Lever, and other job boards frequently ask standard equal opportunity questions. 
                  Simplify Copilot uses these answers to automatically select options and quicken submission.
                </p>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Gender</label>
                  <select
                    value={settings.gender || "Decline to self-identify"}
                    onChange={(e) => setSettings({ ...settings, gender: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    disabled={copilotMigrationPending}
                  >
                    <option value="Male">Male / Man</option>
                    <option value="Female">Female / Woman</option>
                    <option value="Non-binary">Non-binary</option>
                    <option value="Decline to self-identify">Decline to self-identify</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Race / Ethnicity</label>
                  <select
                    value={settings.race || "Decline to self-identify"}
                    onChange={(e) => setSettings({ ...settings, race: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    disabled={copilotMigrationPending}
                  >
                    <option value="White">White / Caucasian</option>
                    <option value="Black or African American">Black or African American</option>
                    <option value="Hispanic or Latino">Hispanic or Latino</option>
                    <option value="Asian">Asian</option>
                    <option value="American Indian or Alaska Native">American Indian or Alaska Native</option>
                    <option value="Native Hawaiian or Other Pacific Islander">Native Hawaiian or Other Pacific Islander</option>
                    <option value="Two or More Races">Two or More Races</option>
                    <option value="Decline to self-identify">Decline to self-identify</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Disability Status</label>
                  <select
                    value={settings.disability_status || "Decline to self-identify"}
                    onChange={(e) => setSettings({ ...settings, disability_status: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    disabled={copilotMigrationPending}
                  >
                    <option value="Yes, I have a disability">Yes, I have a disability (or previously had one)</option>
                    <option value="No, I do not have a disability">No, I do not have a disability</option>
                    <option value="Decline to self-identify">Decline to self-identify</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">Protected Veteran Status</label>
                  <select
                    value={settings.veteran_status || "Decline to self-identify"}
                    onChange={(e) => setSettings({ ...settings, veteran_status: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 transition text-slate-200"
                    disabled={copilotMigrationPending}
                  >
                    <option value="I am a protected veteran">I am a protected veteran</option>
                    <option value="I am not a protected veteran">I am not a protected veteran</option>
                    <option value="Decline to self-identify">Decline to self-identify</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-between">
            {settingsMessage && (
              <div className="text-xs text-indigo-400 font-bold bg-indigo-500/5 px-4 py-2 border border-indigo-500/10 rounded-xl">
                {settingsMessage}
              </div>
            )}
            
            <button
              type="submit"
              disabled={savingSettings || migrationPending}
              className="flex items-center space-x-1.5 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-sm font-semibold text-white transition disabled:bg-indigo-800 disabled:text-slate-400 ml-auto cursor-pointer shadow-lg shadow-indigo-950/20"
            >
              {savingSettings ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>Save Configuration</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Tab 2: Resume Profile & JSON (Original UI) */}
      {activeTab === "resume" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Upload Panel */}
          <div className="lg:col-span-1 space-y-6">
            <div className="glass-card rounded-2xl p-6 space-y-4">
              <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
                <Upload className="h-5 w-5 text-indigo-500" />
                <h3 className="text-base font-bold">Base Profile Resume</h3>
              </div>
              
              <p className="text-xs text-slate-400 leading-relaxed">
                Upload a standard copy of your CV (PDF or DOCX). 
                The system will automatically parse the layout, compute search vectors, and save them for matching.
              </p>

              <div className="pt-2">
                <label className="flex flex-col items-center justify-center w-full h-32 border border-dashed border-slate-800 hover:border-indigo-500/50 rounded-xl cursor-pointer bg-slate-950/20 hover:bg-slate-950/50 transition">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    {uploading ? (
                      <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
                    ) : (
                      <>
                        <Upload className="h-8 w-8 text-slate-500 mb-2" />
                        <p className="text-xs text-slate-400 font-medium">Click to select document</p>
                        <p className="text-[10px] text-slate-600 mt-1">PDF or DOCX</p>
                      </>
                    )}
                  </div>
                  <input 
                    type="file" 
                    accept=".pdf,.docx" 
                    onChange={handleFileUpload} 
                    disabled={uploading}
                    className="hidden" 
                  />
                </label>
              </div>

              {resume && (
                <div className="p-4 bg-slate-950 border border-slate-850 rounded-xl flex items-center space-x-3 text-xs">
                  <FileText className="h-5 w-5 text-indigo-400 flex-shrink-0" />
                  <div className="truncate">
                    <p className="font-bold text-slate-200 truncate">Latest Profile Active</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Uploaded at: {new Date(resume.uploaded_at).toLocaleString()}</p>
                  </div>
                </div>
              )}
            </div>

            {resumeMessage && (
              <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-2xl flex items-start space-x-2.5">
                <AlertCircle className="h-5 w-5 text-indigo-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-slate-300">{resumeMessage}</p>
              </div>
            )}
          </div>

          {/* Right Column: JSON Structured Editor */}
          <div className="lg:col-span-2 glass-card rounded-2xl p-6 flex flex-col min-h-[50vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div className="flex items-center space-x-2">
                <Settings className="h-5 w-5 text-indigo-500" />
                <h3 className="text-base font-bold">Structured Resume Editor (JSON)</h3>
              </div>
              
              <button
                onClick={handleSaveResumeJson}
                disabled={savingResume || !resume}
                className="flex items-center space-x-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white transition disabled:bg-indigo-800 disabled:text-slate-400 cursor-pointer"
              >
                {savingResume ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    <span>Save Profile</span>
                  </>
                )}
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              Directly customize the parsed fields the AI Job Agent reads. Ensure you maintain correct JSON arrays/objects configuration.
            </p>

            <div className="flex-1 flex flex-col">
              <textarea
                value={resumeJsonStr}
                onChange={(e) => setResumeJsonStr(e.target.value)}
                disabled={!resume}
                className="w-full flex-1 min-h-[450px] bg-slate-950 border border-slate-850 rounded-xl p-4 text-xs font-mono text-indigo-300 leading-relaxed focus:outline-none focus:border-indigo-500 transition resize-none disabled:text-slate-600 disabled:border-slate-900"
                placeholder={resume ? "Loading resume details..." : "Please upload a resume first to view parsed contents."}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
