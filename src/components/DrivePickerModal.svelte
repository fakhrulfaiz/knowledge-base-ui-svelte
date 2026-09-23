<script lang="ts">
  import {
    X,
    HardDrive,
    Folder,
    FolderOpen,
    Check,
    Search,
    ArrowRight,
    User,
    Users,
    Building2,
    FileText,
    FileType,
    FileCode,
    Sparkles,
    Loader2,
    CheckCircle2,
    AlertCircle
  } from '@lucide/svelte';
  import { DRIVE_FILES, DRIVE_FOLDERS } from '../data/mockData';
  import type { Collection, DocumentItem, DriveFile, IngestionConfig } from '../types';
  import { chunkTextIntoPages } from '../utils/chunker';

  interface Props {
    collection: Collection;
    existingDocTitles: string[];
    ingestionConfig?: IngestionConfig;
    onClose: () => void;
    onImportComplete: (newDocs: DocumentItem[]) => boolean | void;
  }

  let {
    collection,
    existingDocTitles,
    ingestionConfig,
    onClose,
    onImportComplete,
  }: Props = $props();

  // Active Drive Scope: 'mine' (Personal Drive), 'team' (Team Drive), 'org' (Organization Drive)
  let selectedDriveScope = $state<'mine' | 'team' | 'org'>('org');

  $effect(() => {
    selectedDriveScope = collection.scope === 'mine' ? 'mine' : collection.scope === 'team' ? 'team' : 'org';
  });

  // Filter folders by active drive scope
  let scopedFolders = $derived(
    DRIVE_FOLDERS.filter((f) => f.scope === selectedDriveScope)
  );

  // Selected folder within the active scope
  let selectedFolderId = $state<string>('');

  // Keep folder selected when scope changes
  $effect(() => {
    if (scopedFolders.length > 0) {
      const exists = scopedFolders.some((f) => f.id === selectedFolderId);
      if (!exists) {
        selectedFolderId = scopedFolders[0].id;
      }
    } else {
      selectedFolderId = '';
    }
  });

  // Local state for files (so user can extract raw files in real-time)
  let driveFiles = $state<DriveFile[]>(JSON.parse(JSON.stringify(DRIVE_FILES)));

  let selectedFileIds = $state<Set<string>>(new Set());
  let searchQuery = $state('');
  let isIngesting = $state(false);
  let ingestionStep = $state<string>('');
  let extractingFileId = $state<string | null>(null);

  let activeFolder = $derived(
    scopedFolders.find((f) => f.id === selectedFolderId) || scopedFolders[0]
  );

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
      return file.folderId === selectedFolderId;
    });
  });

  // Check if any selected files require extraction before ingesting
  let hasUnextractedSelected = $derived(
    Array.from(selectedFileIds).some((id) => {
      const f = driveFiles.find((file) => file.id === id);
      return f && f.extractorStatus !== 'extracted';
    })
  );

  function toggleFileSelect(fileId: string) {
    const next = new Set(selectedFileIds);
    if (next.has(fileId)) {
      next.delete(fileId);
    } else {
      next.add(fileId);
    }
    selectedFileIds = next;
  }

  // Extract a single raw file via simulated Extractor Service
  async function handleExtractSingle(e: MouseEvent, fileId: string) {
    e.stopPropagation();
    extractingFileId = fileId;
    await new Promise((r) => setTimeout(r, 600));

    driveFiles = driveFiles.map((f) =>
      f.id === fileId
        ? {
            ...f,
            extractorStatus: 'extracted',
            extractedAt: new Date().toISOString(),
          }
        : f
    );

    extractingFileId = null;
    // Auto-select once extracted
    const next = new Set(selectedFileIds);
    next.add(fileId);
    selectedFileIds = next;
  }

  async function handleImport() {
    if (selectedFileIds.size === 0) return;

    isIngesting = true;
    const selectedFiles = driveFiles.filter((f) => selectedFileIds.has(f.id));

    // Phase 1: If any selected files are not yet extracted, run Extractor Service first
    const unextracted = selectedFiles.filter((f) => f.extractorStatus !== 'extracted');
    if (unextracted.length > 0) {
      ingestionStep = `Extractor Service: Parsing ${unextracted.length} raw document stream(s)...`;
      await new Promise((r) => setTimeout(r, 650));

      driveFiles = driveFiles.map((f) =>
        selectedFileIds.has(f.id)
          ? {
              ...f,
              extractorStatus: 'extracted',
              extractedAt: new Date().toISOString(),
            }
          : f
      );
    }

    // Phase 2: Ingestion Service (chunking + embedding generation)
    ingestionStep = 'Knowledge Base: Tokenizing windows & deep-link spans...';
    await new Promise((r) => setTimeout(r, 450));

    ingestionStep = `Knowledge Base: Generating embeddings & indexing into ${collection.name}...`;
    await new Promise((r) => setTimeout(r, 400));

    const newDocs: DocumentItem[] = selectedFiles.map((file) => {
      const docId = `doc-${Date.now()}-${file.id}`;
      const pages = chunkTextIntoPages(
        docId,
        collection.id,
        collection.scope,
        file.rawContent.pages,
        ingestionConfig
      );
      const totalChunks = pages.reduce((acc, p) => acc + p.chunks.length, 0);

      const folder = DRIVE_FOLDERS.find((f) => f.id === file.folderId);
      const drivePath = `${folder?.path || ''}/${file.filename}`;

      return {
        id: docId,
        collectionId: collection.id,
        title: file.title,
        filename: file.filename,
        fileType: file.fileType,
        source: 'drive',
        drivePath,
        uploadedAt: new Date().toISOString(),
        uploadedBy: file.author,
        sizeBytes: file.sizeBytes,
        pageCount: pages.length,
        chunkCount: totalChunks,
        summary: file.previewSummary,
        entities: file.rawContent.entities,
        crossReferences: [],
        semanticTopics: file.rawContent.semanticTopics,
        pages,
      };
    });

    const success = onImportComplete(newDocs);
    isIngesting = false;
    if (success !== false) {
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
  <div class="w-full max-w-4xl h-[82vh] bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3">
        <div class="p-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 border border-neutral-200 dark:border-neutral-700">
          <HardDrive class="w-4 h-4" />
        </div>
        <div>
          <h2 id="drive-modal-title" class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Upload from Corporate Drive
          </h2>
          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
            <span>Target:</span>
            <strong class="text-neutral-700 dark:text-neutral-300 font-medium">{collection.name}</strong>
            <span>·</span>
            <span class="uppercase font-mono text-[10px] text-blue-600 dark:text-blue-400 font-semibold">{collection.scope}</span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onclick={onClose}
        class="p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 rounded-md transition-colors cursor-pointer"
        title="Close (Esc)"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Scope Selection Strip (Step 1: Choose Drive Scope) -->
    <div class="px-6 py-2.5 bg-neutral-50/80 dark:bg-neutral-900/60 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-4 shrink-0">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
          Drive Scope:
        </span>
        <div class="flex items-center p-0.5 bg-neutral-200/70 dark:bg-neutral-800 rounded-lg text-xs">
          <!-- Personal Scope -->
          <button
            type="button"
            onclick={() => {
              selectedDriveScope = 'mine';
              searchQuery = '';
            }}
            class="flex items-center gap-1.5 px-3 py-1 rounded-md transition-colors cursor-pointer font-medium {selectedDriveScope === 'mine'
              ? 'bg-white dark:bg-neutral-900 text-blue-600 dark:text-blue-400 font-semibold shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <User class="w-3.5 h-3.5" />
            <span>Personal Drive</span>
          </button>

          <!-- Team Scope -->
          <button
            type="button"
            onclick={() => {
              selectedDriveScope = 'team';
              searchQuery = '';
            }}
            class="flex items-center gap-1.5 px-3 py-1 rounded-md transition-colors cursor-pointer font-medium {selectedDriveScope === 'team'
              ? 'bg-white dark:bg-neutral-900 text-blue-600 dark:text-blue-400 font-semibold shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Users class="w-3.5 h-3.5" />
            <span>Team Drive</span>
          </button>

          <!-- Organization Scope -->
          <button
            type="button"
            onclick={() => {
              selectedDriveScope = 'org';
              searchQuery = '';
            }}
            class="flex items-center gap-1.5 px-3 py-1 rounded-md transition-colors cursor-pointer font-medium {selectedDriveScope === 'org'
              ? 'bg-white dark:bg-neutral-900 text-blue-600 dark:text-blue-400 font-semibold shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Building2 class="w-3.5 h-3.5" />
            <span>Organization Drive</span>
          </button>
        </div>
      </div>

      <div class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono">
        {scopedFolders.length} folder(s) available
      </div>
    </div>

    <!-- Ingesting Progress Overlay -->
    {#if isIngesting}
      <div class="absolute inset-0 z-20 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center">
        <div class="w-10 h-10 rounded-full border-3 border-neutral-300 dark:border-neutral-700 border-t-blue-600 dark:border-t-blue-400 animate-spin mb-3"></div>
        <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          Processing Drive Pipeline
        </h3>
        <p class="text-xs text-neutral-600 dark:text-neutral-400 font-mono mt-1 max-w-md bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-md border border-neutral-200 dark:border-neutral-700">
          {ingestionStep}
        </p>
      </div>
    {/if}

    <!-- Main Drive Browser Split: Folders on Left, Files on Right -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Step 2: Folders List -->
      <div class="w-60 bg-neutral-50 dark:bg-neutral-950 border-r border-neutral-200 dark:border-neutral-800 p-3 flex flex-col text-xs shrink-0">
        <div class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2 px-1">
          Folders ({selectedDriveScope})
        </div>

        <div class="space-y-1">
          {#each scopedFolders as folder (folder.id)}
            {@const isSelected = selectedFolderId === folder.id}
            {@const fileCountInFolder = driveFiles.filter((f) => f.folderId === folder.id).length}

            <button
              type="button"
              onclick={() => {
                selectedFolderId = folder.id;
                searchQuery = '';
              }}
              class="w-full text-left px-2.5 py-2 rounded-lg flex items-center justify-between transition-colors cursor-pointer {isSelected
                ? 'bg-blue-600 text-white font-medium shadow-2xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200/60 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-neutral-100'}"
            >
              <div class="flex items-center gap-2 truncate">
                {#if isSelected}
                  <FolderOpen class="w-3.5 h-3.5 shrink-0" />
                {:else}
                  <Folder class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 shrink-0" />
                {/if}
                <span class="truncate">{folder.name}</span>
              </div>
              <span class="text-[10px] font-mono tabular-nums opacity-75">
                {fileCountInFolder}
              </span>
            </button>
          {/each}
        </div>

        <!-- Pipeline Architecture Note (Enterprise Informational) -->
        <div class="mt-auto p-2.5 rounded-lg bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-500 dark:text-neutral-400 space-y-1">
          <div class="font-semibold text-neutral-700 dark:text-neutral-300 flex items-center gap-1">
            <Sparkles class="w-3 h-3 text-blue-600 dark:text-blue-400" />
            <span>Extractor Pipeline</span>
          </div>
          <p class="leading-relaxed text-[10px]">
            Knowledge Base only ingests extracted text into vector chunks. Raw files can be extracted on-demand.
          </p>
        </div>
      </div>

      <!-- Step 3: Files Table View -->
      <div class="flex-1 flex flex-col overflow-hidden bg-white dark:bg-neutral-900">
        <!-- Filter & Search Bar -->
        <div class="p-3 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-3">
          <div class="relative flex-1">
            <Search class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search documents in {activeFolder?.name || 'this folder'}..."
              bind:value={searchQuery}
              class="w-full pl-8 pr-3 py-1.5 text-xs bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-blue-500"
            />
          </div>

          <div class="text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums shrink-0">
            {selectedFileIds.size} selected
          </div>
        </div>

        <!-- Files List with Extractor Status Column -->
        <div class="flex-1 overflow-y-auto p-3 space-y-2">
          {#if visibleFiles.length === 0}
            <div class="h-40 flex flex-col items-center justify-center text-center text-xs text-neutral-400">
              <FileText class="w-6 h-6 mb-1 opacity-40" />
              <span>No files found in this folder.</span>
            </div>
          {:else}
            {#each visibleFiles as file (file.id)}
              {@const isSelected = selectedFileIds.has(file.id)}
              {@const isAlreadyIngested = existingDocTitles.includes(file.title)}
              {@const isExtracted = file.extractorStatus === 'extracted'}
              {@const isExtracting = extractingFileId === file.id}

              <div
                role="button"
                tabindex="0"
                onclick={() => !isAlreadyIngested && toggleFileSelect(file.id)}
                onkeydown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && !isAlreadyIngested) toggleFileSelect(file.id); }}
                class="p-3 rounded-lg border text-xs transition-all flex items-center justify-between gap-3 {isAlreadyIngested
                  ? 'opacity-60 bg-neutral-50 dark:bg-neutral-800/40 border-neutral-200 dark:border-neutral-800 cursor-not-allowed'
                  : isSelected
                  ? 'bg-blue-50/60 dark:bg-blue-950/40 border-blue-400 dark:border-blue-800 cursor-pointer shadow-2xs'
                  : 'bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 border-neutral-200 dark:border-neutral-800 cursor-pointer'}"
              >
                <!-- Checkbox + File Info -->
                <div class="flex items-center gap-3 min-w-0">
                  <div
                    class="w-4 h-4 rounded border flex items-center justify-center shrink-0 {isSelected
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800'}"
                  >
                    {#if isSelected}
                      <Check class="w-3 h-3 stroke-3" />
                    {/if}
                  </div>

                  <div class="p-2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 shrink-0">
                    {#if file.fileType === 'pdf'}
                      <FileText class="w-4 h-4 text-red-500 dark:text-red-400" />
                    {:else if file.fileType === 'docx'}
                      <FileType class="w-4 h-4 text-blue-500 dark:text-blue-400" />
                    {:else}
                      <FileCode class="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
                    {/if}
                  </div>

                  <div class="min-w-0">
                    <div class="font-medium truncate text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                      <span class="truncate">{file.title}</span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-neutral-100 dark:bg-neutral-800 text-neutral-500 border border-neutral-200 dark:border-neutral-700">
                        {file.fileType}
                      </span>
                    </div>

                    <div class="text-[11px] text-neutral-400 dark:text-neutral-500 mt-0.5 flex items-center gap-2 font-mono">
                      <span>{file.filename}</span>
                      <span>·</span>
                      <span>{(file.sizeBytes / (1024 * 1024)).toFixed(1)} MB</span>
                      <span>·</span>
                      <span>Author: {file.author}</span>
                    </div>
                  </div>
                </div>

                <!-- Status & Action Buttons -->
                <div class="flex items-center gap-2 shrink-0">
                  {#if isAlreadyIngested}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-500 border border-neutral-200 dark:border-neutral-700">
                      <CheckCircle2 class="w-3 h-3 text-neutral-400" />
                      <span>In Collection</span>
                    </span>
                  {:else if isExtracted}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                      <CheckCircle2 class="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                      <span>Extracted</span>
                    </span>
                  {:else}
                    <!-- Not Extracted Status + Action to Extract -->
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700">
                      <span>Raw</span>
                    </span>

                    <button
                      type="button"
                      disabled={isExtracting}
                      onclick={(e) => handleExtractSingle(e, file.id)}
                      class="px-2.5 py-1 text-[11px] font-medium rounded border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 transition-colors cursor-pointer flex items-center gap-1"
                      title="Run Extractor Service to parse text and pages"
                    >
                      {#if isExtracting}
                        <Loader2 class="w-3 h-3 animate-spin text-blue-600" />
                        <span>Extracting...</span>
                      {:else}
                        <Sparkles class="w-3 h-3 text-amber-500" />
                        <span>Extract</span>
                      {/if}
                    </button>
                  {/if}
                </div>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="h-14 px-6 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
        <span class="font-mono">{selectedFileIds.size} file(s) selected</span>
        <span>·</span>
        {#if hasUnextractedSelected}
          <span class="text-amber-600 dark:text-amber-400 font-medium">
            Requires extraction before ingest
          </span>
        {:else}
          <span class="text-emerald-600 dark:text-emerald-400 font-medium">
            Ready for embedding &amp; ingestion
          </span>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={onClose}
          class="px-3 py-1.5 text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 font-medium transition-colors cursor-pointer"
        >
          Cancel
        </button>

        <button
          type="button"
          onclick={handleImport}
          disabled={selectedFileIds.size === 0 || isIngesting}
          class="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer"
        >
          {#if hasUnextractedSelected}
            <Sparkles class="w-3.5 h-3.5" />
            <span>Extract &amp; Ingest ({selectedFileIds.size})</span>
          {:else}
            <span>Ingest to Collection ({selectedFileIds.size})</span>
            <ArrowRight class="w-3.5 h-3.5" />
          {/if}
        </button>
      </div>
    </div>
  </div>
</div>
