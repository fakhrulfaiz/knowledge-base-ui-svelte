<script lang="ts">
  import {
    X,
    HardDrive,
    Check,
    Search,
    ArrowRight,
    Users,
    Building2,
    Briefcase,
    FileText,
    Sparkles,
    Loader2,
    CheckCircle2,
    Lock,
    Zap,
    Cpu
  } from '@lucide/svelte';
  import { onMount } from 'svelte';
  import type { Collection, DocumentItem, DriveFile, IngestionConfig } from '../types';
  import { formatBytes } from '../utils/resourceUtils';

  interface Props {
    collection: Collection;
    existingDocTitles: string[];
    ingestionConfig?: IngestionConfig;
    onClose: () => void;
    onImportComplete: (newDocs: DocumentItem[]) => boolean | void;
  }

  let {
    collection,
    existingDocTitles = [],
    ingestionConfig,
    onClose,
    onImportComplete,
  }: Props = $props();

  // Active Drive Scope tab: 'org' | 'team' | 'project' | 'mine' | 'all'
  let selectedDriveScope = $state<'all' | 'org' | 'team' | 'project' | 'mine'>('all');

  // Document Visibility in this collection
  let selectedVisibility = $state<'shared' | 'private'>('shared');

  // Live files from backend /api/drive/files
  let driveFiles = $state<DriveFile[]>([]);
  let isLoadingFiles = $state(true);

  let selectedFileIds = $state<Set<string>>(new Set());
  let searchQuery = $state('');
  let isIngesting = $state(false);
  let ingestionStep = $state<string>('');
  let extractingFilename = $state<string | null>(null);

  async function loadDriveFiles() {
    try {
      isLoadingFiles = true;
      const res = await fetch('http://localhost:8080/api/drive/files');
      if (res.ok) {
        const data = await res.json();
        driveFiles = data.files || [];
      }
    } catch (e) {
      console.warn('Failed to fetch live Drive files from backend:', e);
    } finally {
      isLoadingFiles = false;
    }
  }

  onMount(() => {
    loadDriveFiles();
  });

  let visibleFiles = $derived.by(() => {
    return driveFiles.filter((file) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          file.title.toLowerCase().includes(q) ||
          file.filename.toLowerCase().includes(q) ||
          file.previewSummary.toLowerCase().includes(q)
        );
      }
      if (selectedDriveScope === 'all') return true;
      return file.scope === selectedDriveScope;
    });
  });

  function toggleFileSelect(fileId: string) {
    const next = new Set(selectedFileIds);
    if (next.has(fileId)) {
      next.delete(fileId);
    } else {
      next.add(fileId);
    }
    selectedFileIds = next;
  }

  async function handleExtractSingle(e: MouseEvent, filename: string) {
    e.stopPropagation();
    extractingFilename = filename;
    try {
      const res = await fetch('http://localhost:8080/api/pipeline/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      if (res.ok) {
        await loadDriveFiles();
      }
    } catch (err) {
      console.error('Extract error:', err);
    } finally {
      extractingFilename = null;
    }
  }

  async function handleImport() {
    if (selectedFileIds.size === 0) return;

    isIngesting = true;
    const selectedFiles = driveFiles.filter((f) => selectedFileIds.has(f.id));
    const importedDocs: DocumentItem[] = [];

    for (const file of selectedFiles) {
      const isAlreadyIndexed = file.ingestStatus === 'ingested';

      if (isAlreadyIndexed) {
        ingestionStep = `Ownership linking: Attaching '${file.filename}' to ${collection.name} (Reusing live Milvus vectors)...`;
      } else if (file.extractorStatus !== 'extracted') {
        ingestionStep = `Extractor Service: Extracting structured text from '${file.filename}'...`;
        await fetch('http://localhost:8080/api/pipeline/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: file.filename })
        });
        ingestionStep = `Ingestion Service: Vectorizing and writing to Milvus...`;
      }

      try {
        const res = await fetch(`http://localhost:8080/api/collections/${collection.id}/documents`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.filename,
            title: file.title,
            visibility: selectedVisibility,
            source: 'drive',
            uploadedBy: 'Elena Rostova'
          })
        });

        if (res.ok) {
          const resData = await res.json();
          if (resData.document) {
            importedDocs.push(resData.document);
          }
        }
      } catch (err) {
        console.error('Error adding document:', err);
      }
    }

    isIngesting = false;
    if (importedDocs.length > 0) {
      onImportComplete(importedDocs);
      onClose();
    } else {
      // Fallback close
      onClose();
    }
  }
</script>

<div
  class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none"
  role="dialog"
  aria-modal="true"
  aria-labelledby="drive-modal-title"
>
  <div class="w-full max-w-4xl h-[85vh] bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3">
        <div class="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/80">
          <HardDrive class="w-4 h-4" />
        </div>
        <div>
          <h2 id="drive-modal-title" class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <span>Corporate Drive Explorer</span>
            <span class="text-[11px] font-mono text-neutral-400 font-normal">/data</span>
          </h2>
          <p class="text-[11px] text-neutral-500 dark:text-neutral-400">
            Adding document ownership to: <strong class="text-neutral-800 dark:text-neutral-200 font-medium">{collection.name}</strong>
          </p>
        </div>
      </div>

      <button
        type="button"
        onclick={onClose}
        class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 rounded-lg transition-colors cursor-pointer"
        title="Close (Esc)"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Processing State Overlay -->
    {#if isIngesting}
      <div class="absolute inset-0 z-30 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center">
        <div class="w-12 h-12 rounded-full border-3 border-blue-200 dark:border-blue-900 border-t-blue-600 dark:border-t-blue-400 animate-spin mb-4"></div>
        <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          Knowledge Base Ingestion &amp; Ownership Assignment
        </h3>
        <p class="text-xs text-neutral-600 dark:text-neutral-400 font-mono mt-1.5 max-w-md bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700">
          {ingestionStep}
        </p>
      </div>
    {/if}

    <!-- Toolbar: Search, Scope Tabs & Visibility Choice -->
    <div class="px-6 py-2.5 bg-neutral-50/70 dark:bg-neutral-900/70 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-4 flex-wrap">
      <!-- Search Input -->
      <div class="relative flex-1 min-w-[220px]">
        <Search class="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Filter Drive files in /data..."
          bind:value={searchQuery}
          class="w-full pl-9 pr-3 py-1.5 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-hidden focus:border-blue-500"
        />
      </div>

      <!-- Governance Scope Filter -->
      <div class="flex items-center gap-1 bg-neutral-200/70 dark:bg-neutral-800 p-0.5 rounded-lg text-xs">
        <button
          type="button"
          onclick={() => (selectedDriveScope = 'all')}
          class="px-2.5 py-1 rounded-md transition-colors cursor-pointer {selectedDriveScope === 'all'
            ? 'bg-white dark:bg-neutral-700 font-semibold text-neutral-900 dark:text-neutral-100 shadow-2xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
        >
          All Files ({driveFiles.length})
        </button>
        <button
          type="button"
          onclick={() => (selectedDriveScope = 'org')}
          class="flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors cursor-pointer {selectedDriveScope === 'org'
            ? 'bg-white dark:bg-neutral-700 font-semibold text-neutral-900 dark:text-neutral-100 shadow-2xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
        >
          <Building2 class="w-3 h-3" />
          <span>Org</span>
        </button>
        <button
          type="button"
          onclick={() => (selectedDriveScope = 'team')}
          class="flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors cursor-pointer {selectedDriveScope === 'team'
            ? 'bg-white dark:bg-neutral-700 font-semibold text-neutral-900 dark:text-neutral-100 shadow-2xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
        >
          <Users class="w-3 h-3" />
          <span>Team</span>
        </button>
        <button
          type="button"
          onclick={() => (selectedDriveScope = 'project')}
          class="flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors cursor-pointer {selectedDriveScope === 'project'
            ? 'bg-white dark:bg-neutral-700 font-semibold text-neutral-900 dark:text-neutral-100 shadow-2xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
        >
          <Briefcase class="w-3 h-3" />
          <span>Project</span>
        </button>
      </div>

      <!-- Document Visibility Selector for this Collection -->
      <div class="flex items-center gap-1.5 border-l border-neutral-200 dark:border-neutral-700 pl-4 text-xs">
        <span class="text-neutral-500 text-[11px] font-medium">Visibility:</span>
        <div class="flex items-center gap-1 bg-neutral-200/70 dark:bg-neutral-800 p-0.5 rounded-lg">
          <button
            type="button"
            onclick={() => (selectedVisibility = 'shared')}
            class="flex items-center gap-1 px-2 py-1 rounded-md transition-colors cursor-pointer {selectedVisibility === 'shared'
              ? 'bg-blue-600 text-white font-medium shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
            title="Shared across all members of this collection"
          >
            <Users class="w-3 h-3" />
            <span>Shared</span>
          </button>
          <button
            type="button"
            onclick={() => (selectedVisibility = 'private')}
            class="flex items-center gap-1 px-2 py-1 rounded-md transition-colors cursor-pointer {selectedVisibility === 'private'
              ? 'bg-blue-600 text-white font-medium shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
            title="Personal & Private (visible only to you within this collection)"
          >
            <Lock class="w-3 h-3" />
            <span>Private</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Drive File List Content -->
    <div class="flex-1 overflow-y-auto p-6 space-y-3 custom-scrollbar">
      {#if isLoadingFiles}
        <div class="h-64 flex flex-col items-center justify-center text-neutral-400 text-xs">
          <Loader2 class="w-6 h-6 animate-spin text-blue-500 mb-2" />
          <span>Reading physical files from /data...</span>
        </div>
      {:else if visibleFiles.length === 0}
        <div class="h-64 flex flex-col items-center justify-center text-neutral-400 text-xs">
          <FileText class="w-8 h-8 text-neutral-300 dark:text-neutral-700 mb-2" />
          <span>No documents found matching the filter.</span>
        </div>
      {:else}
        {#each visibleFiles as file (file.id)}
          {@const isSelected = selectedFileIds.has(file.id)}
          {@const isIndexed = file.ingestStatus === 'ingested'}
          {@const isExtracted = file.extractorStatus === 'extracted'}
          {@const isExtracting = extractingFilename === file.filename}

          <div
            role="button"
            tabindex="0"
            onclick={() => toggleFileSelect(file.id)}
            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleFileSelect(file.id); }}
            class="p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-4 {isSelected
              ? 'bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 ring-2 ring-blue-500/20'
              : 'bg-white dark:bg-neutral-850 hover:bg-neutral-50 dark:hover:bg-neutral-800 border-neutral-200 dark:border-neutral-800'}"
          >
            <div class="flex items-center gap-3.5 min-w-0">
              <!-- Checkbox -->
              <div
                class="w-5 h-5 rounded-md border flex items-center justify-center shrink-0 transition-colors {isSelected
                  ? 'bg-blue-600 border-blue-600 text-white'
                  : 'border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800'}"
              >
                {#if isSelected}
                  <Check class="w-3.5 h-3.5" />
                {/if}
              </div>

              <!-- PDF Icon -->
              <div class="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 shrink-0">
                <FileText class="w-5 h-5" />
              </div>

              <!-- File Info -->
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <h4 class="text-xs font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                    {file.title}
                  </h4>
                  <!-- Live Pipeline Badges -->
                  {#if isIndexed}
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 flex items-center gap-1">
                      <Zap class="w-2.5 h-2.5" />
                      <span>Indexed in Milvus (Ready)</span>
                    </span>
                  {:else if isExtracted}
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 flex items-center gap-1">
                      <CheckCircle2 class="w-2.5 h-2.5" />
                      <span>Extracted</span>
                    </span>
                  {:else}
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300">
                      Raw (Not Extracted)
                    </span>
                  {/if}
                </div>

                <div class="flex items-center gap-3 text-[11px] text-neutral-400 mt-1 font-mono">
                  <span>{file.filename}</span>
                  <span>•</span>
                  <span>{formatBytes(file.sizeBytes)}</span>
                  <span>•</span>
                  <span>{file.pageCount || 1} pages</span>
                </div>

                <p class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-1">
                  {file.previewSummary}
                </p>
              </div>
            </div>

            <!-- Single Extractor Action -->
            <div class="shrink-0 flex items-center gap-2">
              {#if !isExtracted}
                <button
                  type="button"
                  disabled={isExtracting}
                  onclick={(e) => handleExtractSingle(e, file.filename)}
                  class="px-2.5 py-1 text-[11px] font-medium bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-md border border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 flex items-center gap-1 cursor-pointer transition-colors"
                >
                  {#if isExtracting}
                    <Loader2 class="w-3 h-3 animate-spin" />
                    <span>Extracting...</span>
                  {:else}
                    <Cpu class="w-3 h-3 text-blue-500" />
                    <span>Run Extractor</span>
                  {/if}
                </button>
              {/if}
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <!-- Footer Bar -->
    <div class="px-6 py-3.5 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="text-xs text-neutral-500">
        {#if selectedFileIds.size > 0}
          <span class="text-blue-600 dark:text-blue-400 font-semibold">{selectedFileIds.size}</span> file(s) selected
          · Will be added with <strong class="text-neutral-800 dark:text-neutral-200">{selectedVisibility.toUpperCase()}</strong> visibility
        {:else}
          Select files from Drive to add ownership to this collection.
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={onClose}
          class="px-3.5 py-1.5 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg text-xs font-medium text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors"
        >
          Cancel
        </button>

        <button
          type="button"
          disabled={selectedFileIds.size === 0 || isIngesting}
          onclick={handleImport}
          class="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-medium shadow-xs cursor-pointer transition-colors"
        >
          <span>Add to Collection</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </div>
</div>
