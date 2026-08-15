import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldCheck, UserCheck, Trash2, Plus, Globe, Tag } from "lucide-react";
import {
  useIdentityAnchor,
  useAddAlias,
  useRevokeAlias,
  useAddProfile,
  useRevokeProfile,
} from "./api";

export function IdentityAnchorView() {
  const anchorQuery = useIdentityAnchor();
  const addAlias = useAddAlias();
  const revokeAlias = useRevokeAlias();
  const addProfile = useAddProfile();
  const revokeProfile = useRevokeProfile();

  const [aliasValue, setAliasValue] = useState("");
  const [aliasType, setAliasType] = useState("username");
  
  const [platform, setPlatform] = useState("");
  const [profileUrl, setProfileUrl] = useState("");

  if (anchorQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      </div>
    );
  }
  if (!anchorQuery.data?.data) return <div className="text-sm font-mono text-slate-400 p-6 text-center border border-white/10 rounded-xl">No identity anchor found.</div>;

  const anchor = anchorQuery.data.data;

  const handleAddAlias = (e: React.FormEvent) => {
    e.preventDefault();
    if (!aliasValue) return;
    addAlias.mutate(
      { alias_type: aliasType, value: aliasValue },
      { onSuccess: () => setAliasValue("") }
    );
  };

  const handleAddProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!platform || !profileUrl) return;
    addProfile.mutate(
      { platform, profile_url: profileUrl },
      { onSuccess: () => { setPlatform(""); setProfileUrl(""); } }
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 border-l-4 border-cyan-400 pl-4 py-1">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Verified Identity Anchor <span className="text-cyan-400 font-mono text-base">v{anchor.version}</span>
          </h2>
          <span className="text-xs font-mono text-slate-400">Cryptographically bound self-only attribution trust root</span>
        </div>
        <Badge variant="outline" className="text-xs font-mono bg-white/[0.03] border-white/15 text-slate-300">
          Updated: {new Date(anchor.updated_at).toLocaleString()}
        </Badge>
      </div>

      <Card className="border-white/10 bg-slate-900/60 shadow-xl backdrop-blur-md">
        <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-4">
          <CardTitle className="text-base font-bold text-white flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
            Verified Identifiers
          </CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Core trust targets (verified email addresses and phone numbers) powering all authorized scans
          </CardDescription>
        </CardHeader>
        <CardContent className="p-4 space-y-2.5">
          {anchor.verified_identifiers.map((i: any) => (
            <div key={i.id} className="flex justify-between items-center rounded-lg border border-white/10 bg-black/20 px-4 py-2.5">
              <div className="flex items-center gap-2.5 min-w-0">
                <Badge variant="outline" className="text-[10px] font-mono uppercase bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shrink-0">
                  {i.type}
                </Badge>
                <span className="font-bold text-slate-200 text-sm truncate">{i.value_display}</span>
              </div>
              <span className="text-xs font-mono text-slate-400 shrink-0">Verified {new Date(i.verified_at).toLocaleDateString()}</span>
            </div>
          ))}
          {!anchor.verified_identifiers.length && (
            <p className="text-xs font-mono text-slate-400 italic text-center py-4">No verified identifiers attached to this anchor.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ALIASES */}
        <Card className="border-white/10 bg-slate-900/60 shadow-xl backdrop-blur-md flex flex-col justify-between">
          <div>
            <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-3">
              <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                <Tag className="h-4 w-4 text-cyan-400" />
                Aliases
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">Usernames or handles you use online</CardDescription>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <form onSubmit={handleAddAlias} className="flex gap-2">
                <select 
                  className="flex h-9 w-[130px] rounded-lg border border-white/15 bg-slate-950 px-3 text-xs font-mono text-white shadow-sm focus:border-cyan-400 focus:outline-none"
                  value={aliasType} 
                  onChange={e => setAliasType(e.target.value)}
                >
                  <option value="username" className="bg-slate-900 text-white">Username</option>
                  <option value="handle" className="bg-slate-900 text-white">Handle</option>
                  <option value="nickname" className="bg-slate-900 text-white">Nickname</option>
                </select>
                <Input 
                  placeholder="e.g. jdoe123" 
                  value={aliasValue} 
                  onChange={e => setAliasValue(e.target.value)} 
                  className="h-9 font-mono text-xs border-white/15 bg-slate-950"
                />
                <Button type="submit" variant="secondary" size="sm" disabled={addAlias.isPending || !aliasValue} className="h-9 px-4 font-semibold">
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add
                </Button>
              </form>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {anchor.active_aliases.map((a: any) => (
                  <div key={a.id} className="flex justify-between items-center rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-mono">
                    <div className="flex items-center gap-2 truncate min-w-0">
                      <Badge variant="secondary" className="text-[10px] uppercase bg-white/[0.05] border-white/15 text-slate-300 shrink-0">
                        {a.alias_type}
                      </Badge>
                      <span className="font-semibold text-white truncate">{a.display_value}</span>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-7 px-2 text-red-400 hover:bg-red-500/20 hover:text-red-300 shrink-0 text-xs font-sans"
                      onClick={() => revokeAlias.mutate(a.id)}
                      disabled={revokeAlias.isPending}
                    >
                      Revoke
                    </Button>
                  </div>
                ))}
                {!anchor.active_aliases.length && <p className="text-xs text-slate-400 font-mono italic text-center py-4">No aliases configured.</p>}
              </div>
            </CardContent>
          </div>
        </Card>

        {/* PROFILES */}
        <Card className="border-white/10 bg-slate-900/60 shadow-xl backdrop-blur-md flex flex-col justify-between">
          <div>
            <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-3">
              <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                <Globe className="h-4 w-4 text-emerald-400" />
                Confirmed Profiles
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">Public web profile URLs matching your verified identity</CardDescription>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <form onSubmit={handleAddProfile} className="space-y-2.5">
                <div className="flex gap-2">
                  <Input 
                    className="w-1/3 h-9 text-xs font-mono border-white/15 bg-slate-950"
                    placeholder="Platform (e.g. github)" 
                    value={platform} 
                    onChange={e => setPlatform(e.target.value)} 
                  />
                  <Input 
                    className="flex-1 h-9 text-xs font-mono border-white/15 bg-slate-950"
                    placeholder="https://github.com/..." 
                    value={profileUrl} 
                    onChange={e => setProfileUrl(e.target.value)} 
                  />
                </div>
                <Button type="submit" variant="secondary" size="sm" disabled={addProfile.isPending || !platform || !profileUrl} className="w-full font-semibold">
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add Profile
                </Button>
              </form>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {anchor.active_confirmed_profiles.map((p: any) => (
                  <div key={p.id} className="flex flex-col rounded-lg border border-white/10 bg-black/20 p-3 text-xs font-mono">
                    <div className="flex justify-between items-center mb-1.5">
                      <Badge variant="secondary" className="text-[10px] uppercase bg-emerald-500/15 text-emerald-300 border-emerald-500/30">
                        {p.platform}
                      </Badge>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-400 hover:bg-red-500/20 hover:text-red-300 h-6 px-2 text-xs font-sans"
                        onClick={() => revokeProfile.mutate(p.id)}
                        disabled={revokeProfile.isPending}
                      >
                        Revoke
                      </Button>
                    </div>
                    <a href={p.profile_url_display} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline break-all text-[11px] truncate font-sans">
                      {p.profile_url_display}
                    </a>
                  </div>
                ))}
                {!anchor.active_confirmed_profiles.length && <p className="text-xs text-slate-400 font-mono italic text-center py-4">No profiles configured.</p>}
              </div>
            </CardContent>
          </div>
        </Card>
      </div>
    </div>
  );
}
