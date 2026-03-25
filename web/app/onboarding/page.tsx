'use client';

/**
 * ADR-140: Context-First Onboarding
 *
 * Onboarding = context enrichment, NOT task creation.
 * Agents are pre-scaffolded at sign-up (6 roster agents).
 * User shares context (files + description + name) → workspace enriched.
 * Task creation is downstream — via TP conversation on workfloor.
 */

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { GrainOverlay } from '@/components/landing/GrainOverlay';
import { HOME_ROUTE } from '@/lib/routes';
import { api } from '@/lib/api/client';
import { Upload, FileText, ArrowRight, Loader2, X } from 'lucide-react';

export default function OnboardingPage() {
  const router = useRouter();
  const [description, setDescription] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; id?: string; status: 'uploading' | 'done' | 'error' }>>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.replace('/auth/login');
      } else {
        const displayName = user.user_metadata?.full_name || user.user_metadata?.name || '';
        if (displayName) setName(displayName);
        setAuthChecking(false);
      }
    });
  }, [router]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files) return;
    for (const file of Array.from(files)) {
      const entry = { name: file.name, status: 'uploading' as const };
      setUploadedFiles(prev => [...prev, entry]);
      try {
        const result = await api.documents.upload(file);
        setUploadedFiles(prev =>
          prev.map(f => f.name === file.name ? { ...f, id: result.document_id, status: 'done' as const } : f)
        );
      } catch {
        setUploadedFiles(prev =>
          prev.map(f => f.name === file.name ? { ...f, status: 'error' as const } : f)
        );
      }
    }
  };

  const removeFile = (fileName: string) => {
    setUploadedFiles(prev => prev.filter(f => f.name !== fileName));
  };

  const hasContent = description.trim().length > 0 || uploadedFiles.some(f => f.status === 'done');

  const handleSubmit = async () => {
    if (!hasContent) return;
    setLoading(true);
    try {
      const documentIds = uploadedFiles.filter(f => f.status === 'done' && f.id).map(f => f.id!);

      await api.onboarding.enrich(
        description.trim(),
        name.trim() || undefined,
        documentIds.length > 0 ? documentIds : undefined,
      );

      router.push(HOME_ROUTE);
    } catch (err) {
      console.error('Onboarding failed:', err);
      setLoading(false);
    }
  };

  if (authChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#faf8f5]">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
      <GrainOverlay />

      <div className="relative z-10 w-full max-w-lg space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-brand text-[#1a1a1a]">yarnnn</h1>
          <p className="mt-2 text-[#1a1a1a]/60">Tell us about your work</p>
        </div>

        <div className="glass-card-light p-8 space-y-5">

          {/* Description — context about their work */}
          <div>
            <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
              What do you do?
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., I'm building an AI agent platform. I track competitors like CrewAI and AutoGen, manage investor relations, and coordinate a small team on Slack."
              rows={3}
              autoFocus
              className="w-full text-sm px-3 py-2 rounded-lg border border-[#1a1a1a]/10 bg-white focus:outline-none focus:ring-2 focus:ring-[#1a1a1a]/10 resize-none"
            />
          </div>

          {/* File upload */}
          <div
            className="border-2 border-dashed border-[#1a1a1a]/15 rounded-xl p-5 text-center hover:border-[#1a1a1a]/30 transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
            onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handleFileUpload(e.dataTransfer.files); }}
          >
            <Upload className="w-6 h-6 text-[#1a1a1a]/25 mx-auto mb-1.5" />
            <p className="text-sm text-[#1a1a1a]/50">Or drop files for more context</p>
            <p className="text-xs text-[#1a1a1a]/30 mt-0.5">Pitch decks, project briefs, strategy docs</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.txt,.md,.docx"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
          </div>

          {uploadedFiles.length > 0 && (
            <div className="space-y-1.5">
              {uploadedFiles.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-xs bg-[#1a1a1a]/5 rounded-lg px-3 py-2">
                  <FileText className="w-3.5 h-3.5 text-[#1a1a1a]/40" />
                  <span className="truncate flex-1 text-[#1a1a1a]/70">{f.name}</span>
                  {f.status === 'uploading' && <Loader2 className="w-3 h-3 animate-spin text-[#1a1a1a]/40" />}
                  {f.status === 'done' && <span className="text-green-600 text-[10px]">done</span>}
                  {f.status === 'error' && <span className="text-red-500 text-[10px]">failed</span>}
                  <button onClick={() => removeFile(f.name)} className="text-[#1a1a1a]/30 hover:text-[#1a1a1a]/60">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Name */}
          <div>
            <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">Your name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>

          {/* Submit */}
          <Button onClick={handleSubmit} disabled={!hasContent || loading} className="w-full">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowRight className="w-4 h-4 mr-2" />}
            {loading ? 'Understanding your work...' : 'Continue'}
          </Button>

          <div className="text-center">
            <button onClick={() => router.push(HOME_ROUTE)} className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors">
              Skip for now
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-[#1a1a1a]/30">
          Your team of 6 agents is already set up. This context helps them do better work.
        </p>
      </div>
    </div>
  );
}
