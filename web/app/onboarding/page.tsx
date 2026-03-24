'use client';

/**
 * ADR-132/136: Work-First Onboarding — Single Step
 *
 * One screen: share context (files + description + name) → submit
 * Inference handles everything: scopes, objectives, brand, team composition
 * User focuses on WHAT they want, system figures out HOW
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

      await api.onboardingScaffold.save(
        [{ name: description.trim() || 'My Work' }],
        name.trim() || undefined,
        undefined, // brand inferred by backend
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
          <p className="mt-2 text-[#1a1a1a]/60">Share what you&apos;re working on</p>
        </div>

        <div className="glass-card-light p-8 space-y-5">

          {/* File upload */}
          <div
            className="border-2 border-dashed border-[#1a1a1a]/15 rounded-xl p-6 text-center hover:border-[#1a1a1a]/30 transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
            onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handleFileUpload(e.dataTransfer.files); }}
          >
            <Upload className="w-7 h-7 text-[#1a1a1a]/25 mx-auto mb-2" />
            <p className="text-sm text-[#1a1a1a]/50">Drop files here</p>
            <p className="text-xs text-[#1a1a1a]/30 mt-1">Pitch decks, project briefs, any docs</p>
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
                  {f.status === 'done' && <span className="text-green-600 text-[10px]">✓</span>}
                  {f.status === 'error' && <span className="text-red-500 text-[10px]">✗</span>}
                  <button onClick={() => removeFile(f.name)} className="text-[#1a1a1a]/30 hover:text-[#1a1a1a]/60">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="relative flex items-center gap-3">
            <div className="flex-1 h-px bg-[#1a1a1a]/10" />
            <span className="text-xs text-[#1a1a1a]/30">and / or</span>
            <div className="flex-1 h-px bg-[#1a1a1a]/10" />
          </div>

          {/* Description — what they want */}
          <div>
            <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
              What do you need?
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., I need weekly competitive intel on AI pricing, a polished investor update every month, and daily Slack recaps of my team's activity."
              rows={3}
              autoFocus
              className="w-full text-sm px-3 py-2 rounded-lg border border-[#1a1a1a]/10 bg-white focus:outline-none focus:ring-2 focus:ring-[#1a1a1a]/10 resize-none"
            />
          </div>

          {/* Name */}
          <div>
            <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">Your name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>

          {/* Submit */}
          <Button onClick={handleSubmit} disabled={!hasContent || loading} className="w-full">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowRight className="w-4 h-4 mr-2" />}
            {loading ? 'Setting up your team...' : 'Set up my team'}
          </Button>

          <div className="text-center">
            <button onClick={() => router.push(HOME_ROUTE)} className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors">
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
