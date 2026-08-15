import React from 'react';
import { IdentityReviewQueue } from './IdentityReviewQueue';
import { ShieldAlert } from 'lucide-react';

export function ReviewQueuePage() {
  return (
    <div className="p-6 md:p-8 bg-slate-950 min-h-screen text-slate-200">
      <header className="mb-8 flex items-center gap-3">
        <div className="bg-amber-500/20 p-2.5 rounded-lg border border-amber-500/30">
          <ShieldAlert className="w-6 h-6 text-amber-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Review Queue</h1>
          <p className="text-slate-400 mt-1">Review and resolve identity change alerts that require your attention.</p>
        </div>
      </header>

      <main>
        <IdentityReviewQueue />
      </main>
    </div>
  );
}
