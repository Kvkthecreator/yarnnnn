'use client';

/**
 * ADR-132/136: Work-First Onboarding (Redesigned)
 *
 * Two-step flow:
 * Step 1: Share context — upload files + describe work (both optional, at least one)
 * Step 2: Brand basics + name → submit
 *
 * On submit: inference extracts scopes → scaffold_project() per scope → redirect
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
  const [step, setStep] = useState<1 | 2>(1);
  const [description, setDescription] = useState('');
  const [name, setName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [brandTone, setBrandTone] = useState('');
  const [loading, setLoading] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);

  // File upload state
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; id?: string; status: 'uploading' | 'done' | 'error' }>>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auth guard
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
      let brandContent: string | undefined;
      if (companyName.trim() || brandTone.trim()) {
        const brandLines = [`# Brand: ${companyName.trim() || 'Default'}`, ''];
        if (brandTone.trim()) brandLines.push('## Tone', brandTone.trim(), '');
        brandContent = brandLines.join('\n');
      }

      const documentIds = uploadedFiles.filter(f => f.status === 'done' && f.id).map(f => f.id!);

      // Send description as a single "project" name — inference will extract multiple scopes
      await api.onboardingScaffold.save(
        [{ name: description.trim() || 'My Work' }],
        name.trim() || undefined,
        brandContent,
        documentIds.length > 0 ? documentIds : undefined,
      );

      router.push(HOME_ROUTE);
    } catch (err) {
      console.error('Onboarding failed:', err);
      setLoading(false);
    }
  };

  const handleSkip = () => router.push(HOME_ROUTE);

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
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-brand text-[#1a1a1a]">yarnnn</h1>
          <p className="mt-2 text-[#1a1a1a]/60">
            {step === 1
              ? 'Share what you\'re working on'
              : 'Almost there'}
          </p>
        </div>

        {/* Step 1: Share context */}
        {step === 1 && (
          <div className="glass-card-light p-8 space-y-5">

            {/* File upload zone */}
            <div>
              <label className="text-sm font-medium text-[#1a1a1a]/70 mb-2 block">
                Upload files for context
              </label>
              <div
                className="border-2 border-dashed border-[#1a1a1a]/15 rounded-xl p-8 text-center hover:border-[#1a1a1a]/30 transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handleFileUpload(e.dataTransfer.files); }}
              >
                <Upload className="w-8 h-8 text-[#1a1a1a]/25 mx-auto mb-3" />
                <p className="text-sm text-[#1a1a1a]/50">Drop files here or click to browse</p>
                <p className="text-xs text-[#1a1a1a]/30 mt-1">Pitch decks, project briefs, docs — we&apos;ll figure out the rest</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.txt,.md,.docx"
                  className="hidden"
                  onChange={(e) => handleFileUpload(e.target.files)}
                />
              </div>
            </div>

            {/* Uploaded files */}
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

            {/* Divider */}
            <div className="relative flex items-center gap-3 py-1">
              <div className="flex-1 h-px bg-[#1a1a1a]/10" />
              <span className="text-xs text-[#1a1a1a]/30">and / or</span>
              <div className="flex-1 h-px bg-[#1a1a1a]/10" />
            </div>

            {/* Text description */}
            <div>
              <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                Describe your work
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., I run an AI startup called yarnnn. I need to track competitors, monitor my Slack, and produce weekly investor updates."
                rows={3}
                className="w-full text-sm px-3 py-2 rounded-lg border border-[#1a1a1a]/10 bg-white focus:outline-none focus:ring-2 focus:ring-[#1a1a1a]/10 resize-none"
              />
            </div>

            {/* Next */}
            <Button
              onClick={() => setStep(2)}
              disabled={!hasContent}
              className="w-full"
            >
              <ArrowRight className="w-4 h-4 mr-2" />
              Next
            </Button>

            <div className="text-center">
              <button onClick={handleSkip} className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors">
                Skip for now
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Brand + Name + Submit */}
        {step === 2 && (
          <div className="glass-card-light p-8 space-y-5">
            <button onClick={() => setStep(1)} className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors">
              &larr; Back
            </button>

            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">Your name</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoFocus />
              </div>
              <div>
                <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">Company or brand name</label>
                <Input value={companyName} onChange={(e) => setCompanyName(e.target.value)} placeholder="e.g., Acme Corp" />
              </div>
              <div>
                <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">How should outputs sound?</label>
                <Input value={brandTone} onChange={(e) => setBrandTone(e.target.value)} placeholder="e.g., Professional and concise" />
              </div>
            </div>

            <Button onClick={handleSubmit} disabled={!hasContent || loading} className="w-full">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowRight className="w-4 h-4 mr-2" />}
              {loading ? 'Setting up your team...' : 'Get Started'}
            </Button>

            <div className="text-center">
              <button onClick={handleSkip} className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors">
                Skip for now
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
