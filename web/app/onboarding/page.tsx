'use client';

/**
 * ADR-132: Work-First Onboarding
 *
 * Lightweight two-step onboarding page shown once after signup.
 * Step 1: "How is your work structured?" — single vs multi-scope
 * Step 2: Define work scopes + name
 *
 * On submit: saves /memory/WORK.md + updates profile name → redirects to /orchestrator
 * On skip: redirects to /orchestrator (current platform-first bootstrap as fallback)
 */

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { GrainOverlay } from '@/components/landing/GrainOverlay';
import { HOME_ROUTE } from '@/lib/routes';
import { api } from '@/lib/api/client';
import { Briefcase, Layers, Plus, X, ArrowRight, Loader2, Upload, FileText } from 'lucide-react';

type WorkStructure = 'single' | 'multi' | null;

interface ScopeEntry {
  id: string;
  name: string;
}

const PLACEHOLDER_EXAMPLES = [
  'e.g., "My SaaS startup"',
  'e.g., "Acme Corp project"',
  'e.g., "Sales pipeline"',
  'e.g., "Product development"',
  'e.g., "Marketing"',
  'e.g., "Fundraising"',
];

function getPlaceholder(index: number): string {
  return PLACEHOLDER_EXAMPLES[index % PLACEHOLDER_EXAMPLES.length];
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [structure, setStructure] = useState<WorkStructure>(null);
  const [scopes, setScopes] = useState<ScopeEntry[]>([
    { id: '1', name: '' },
  ]);
  const [name, setName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [brandTone, setBrandTone] = useState('');
  const [loading, setLoading] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  // ADR-136: File upload for context inference
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; id?: string; status: 'uploading' | 'done' | 'error' }>>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auth guard — redirect to login if not authenticated
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.replace('/auth/login');
      } else {
        // Pre-fill name from auth metadata if available
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

  const handleStructureSelect = (s: WorkStructure) => {
    setStructure(s);
    if (s === 'multi') {
      setScopes([
        { id: '1', name: '' },
        { id: '2', name: '' },
      ]);
    } else {
      setScopes([{ id: '1', name: '' }]);
    }
    setStep(2);
  };

  const addScope = () => {
    setScopes((prev) => [
      ...prev,
      { id: String(Date.now()), name: '' },
    ]);
  };

  const removeScope = (id: string) => {
    if (scopes.length <= 1) return;
    setScopes((prev) => prev.filter((s) => s.id !== id));
  };

  const updateScope = (id: string, name: string) => {
    setScopes((prev) =>
      prev.map((s) => (s.id === id ? { ...s, name } : s))
    );
  };

  const handleTopicsNext = () => {
    const validScopes = scopes.filter((s) => s.name.trim());
    if (validScopes.length === 0 || !structure) return;
    setStep(3);
  };

  const handleSubmit = async () => {
    const validScopes = scopes.filter((s) => s.name.trim());
    if (validScopes.length === 0 || !structure) return;

    setLoading(true);
    try {
      // Build brand content if provided
      let brandContent: string | undefined;
      if (companyName.trim() || brandTone.trim()) {
        const brandLines = [`# Brand: ${companyName.trim() || 'Default'}`, ''];
        if (brandTone.trim()) {
          brandLines.push('## Tone', brandTone.trim(), '');
        }
        brandContent = brandLines.join('\n');
        // Backend saves to /workspace/BRAND.md and seeds into projects
      }

      // Scaffold projects — identity + brand seeded from /workspace/ by scaffold_project()
      const documentIds = uploadedFiles.filter(f => f.status === 'done' && f.id).map(f => f.id!);
      await api.onboardingScaffold.save(
        validScopes.map((s) => ({ name: s.name.trim() })),
        name.trim() || undefined,
        brandContent,
        documentIds.length > 0 ? documentIds : undefined,
      );

      router.push(HOME_ROUTE);
    } catch (err) {
      console.error('Failed to save onboarding data:', err);
      setLoading(false);
    }
  };

  const handleSkip = () => {
    router.push(HOME_ROUTE);
  };

  const hasContent = scopes.some((s) => s.name.trim()) || uploadedFiles.some(f => f.status === 'done');
  const canSubmit = structure && hasContent && !loading;

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
              ? 'How is your work structured?'
              : step === 2
                ? (structure === 'single'
                    ? 'What are you working on?'
                    : 'What are the things you\'re juggling?')
                : 'Tell us about your brand'}
          </p>
        </div>

        {/* Step 1: Work structure selection */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleStructureSelect('single')}
                className="glass-card-light p-6 text-left hover:ring-2 hover:ring-[#1a1a1a]/20 transition-all cursor-pointer group"
              >
                <Briefcase className="w-6 h-6 text-[#1a1a1a]/60 mb-3 group-hover:text-[#1a1a1a]" />
                <div className="font-medium text-[#1a1a1a]">I focus on one thing</div>
                <p className="text-sm text-[#1a1a1a]/50 mt-1">
                  One product, company, or domain
                </p>
              </button>

              <button
                onClick={() => handleStructureSelect('multi')}
                className="glass-card-light p-6 text-left hover:ring-2 hover:ring-[#1a1a1a]/20 transition-all cursor-pointer group"
              >
                <Layers className="w-6 h-6 text-[#1a1a1a]/60 mb-3 group-hover:text-[#1a1a1a]" />
                <div className="font-medium text-[#1a1a1a]">I juggle multiple things</div>
                <p className="text-sm text-[#1a1a1a]/50 mt-1">
                  Multiple projects, workstreams, or areas
                </p>
              </button>
            </div>

            <div className="text-center">
              <button
                onClick={handleSkip}
                className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors"
              >
                Skip and explore on your own
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Define scopes */}
        {step === 2 && (
          <div className="glass-card-light p-8 space-y-5">
            {/* Back button */}
            <button
              onClick={() => setStep(1)}
              className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors"
            >
              &larr; Back
            </button>

            {/* File upload zone — share existing docs for context */}
            <div
              className="border-2 border-dashed border-[#1a1a1a]/15 rounded-xl p-6 text-center hover:border-[#1a1a1a]/30 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
              onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handleFileUpload(e.dataTransfer.files); }}
            >
              <Upload className="w-6 h-6 text-[#1a1a1a]/30 mx-auto mb-2" />
              <p className="text-sm text-[#1a1a1a]/50">
                Drop files here to share context
              </p>
              <p className="text-xs text-[#1a1a1a]/30 mt-1">
                Pitch decks, project briefs, docs — we&apos;ll figure out the rest
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
              />
            </div>

            {/* Uploaded files */}
            {uploadedFiles.length > 0 && (
              <div className="space-y-1">
                {uploadedFiles.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-[#1a1a1a]/60">
                    <FileText className="w-3 h-3" />
                    <span className="truncate">{f.name}</span>
                    {f.status === 'uploading' && <Loader2 className="w-3 h-3 animate-spin" />}
                    {f.status === 'done' && <span className="text-green-600">✓</span>}
                    {f.status === 'error' && <span className="text-red-500">✗</span>}
                  </div>
                ))}
              </div>
            )}

            <div className="relative flex items-center gap-3 py-1">
              <div className="flex-1 h-px bg-[#1a1a1a]/10" />
              <span className="text-xs text-[#1a1a1a]/30">or describe your work</span>
              <div className="flex-1 h-px bg-[#1a1a1a]/10" />
            </div>

            {/* Scope inputs */}
            <div className="space-y-3">
              {structure === 'single' ? (
                <div>
                  <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                    Describe your work
                  </label>
                  <Input
                    value={scopes[0]?.name || ''}
                    onChange={(e) => updateScope(scopes[0]?.id || '1', e.target.value)}
                    placeholder={getPlaceholder(0)}
                    autoFocus
                  />
                </div>
              ) : (
                <>
                  <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                    Name each one
                  </label>
                  {scopes.map((scope, i) => (
                    <div key={scope.id} className="flex items-center gap-2">
                      <Input
                        value={scope.name}
                        onChange={(e) => updateScope(scope.id, e.target.value)}
                        placeholder={getPlaceholder(i + 1)}
                        autoFocus={i === 0}
                      />
                      {scopes.length > 1 && (
                        <button
                          onClick={() => removeScope(scope.id)}
                          className="shrink-0 p-1.5 text-[#1a1a1a]/30 hover:text-[#1a1a1a]/60 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={addScope}
                    className="flex items-center gap-1.5 text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add another
                  </button>
                </>
              )}
            </div>

            {/* Name field */}
            <div>
              <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                Your name
              </label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
              />
            </div>

            {/* Next → Brand step */}
            <Button
              onClick={handleTopicsNext}
              disabled={!hasContent}
              className="w-full"
            >
              <ArrowRight className="w-4 h-4 mr-2" />
              Next
            </Button>

            <div className="text-center">
              <button
                onClick={handleSkip}
                className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors"
              >
                Skip for now
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Brand basics (optional) */}
        {step === 3 && (
          <div className="glass-card-light p-8 space-y-5">
            <button
              onClick={() => setStep(2)}
              className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors"
            >
              &larr; Back
            </button>

            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                  Company or brand name
                </label>
                <Input
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g., Acme Corp"
                  autoFocus
                />
              </div>

              <div>
                <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                  How should your outputs sound?
                </label>
                <Input
                  value={brandTone}
                  onChange={(e) => setBrandTone(e.target.value)}
                  placeholder="e.g., Professional and concise"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-[#1a1a1a]/70 mb-1.5 block">
                  Your name
                </label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                />
              </div>
            </div>

            <Button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="w-full"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <ArrowRight className="w-4 h-4 mr-2" />
              )}
              Get Started
            </Button>

            <div className="text-center">
              <button
                onClick={handleSkip}
                className="text-sm text-[#1a1a1a]/40 hover:text-[#1a1a1a]/60 transition-colors"
              >
                Skip for now
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
