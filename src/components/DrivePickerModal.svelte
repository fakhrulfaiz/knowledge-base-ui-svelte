<script lang="ts">
  import {
    X,
    HardDrive,
    Folder,
    FolderOpen,
    Check,
    Search,
    ArrowRight
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

  let selectedFolderId = $state<string>('f-sec');
  let selectedFileIds = $state<Set<string>>(new Set(['drv-file-01']));
  let searchQuery = $state('');
  let isIngesting = $state(false);
  let ingestionStep = $state<string>('');

  let visibleFiles = $derived.by(() => {
    return DRIVE_FILES.filter((file) => {
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

  function toggleFileSelect(fileId: string) {
    const next = new Set(selectedFileIds);
    if (next.has(fileId)) {
      next.delete(fileId);
    } else {
      next.add(fileId);
    }
    selectedFileIds = next;
  }

  async function handleImport() {
    if (selectedFileIds.size === 0) return;

    isIngesting = true;
    ingestionStep = 'Connecting to Google Drive...';
    await new Promise((r) => setTimeout(r, 400));

    ingestionStep = 'Extracting document pages and sections...';
    await new Promise((r) => setTimeout(r, 450));

    ingestionStep = 'Indexing for search and retrieval...';
    await new Promise((r) => setTimeout(r, 350));

    const selectedFiles = DRIVE_FILES.filter((f) => selectedFileIds.has(f.id));

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

      return {
        id: docId,
        collectionId: collection.id,
        title: file.title,
        filename: file.filename,
        fileType: file.fileType,
        source: 'drive',
        drivePath: `${DRIVE_FOLDERS.find((f) => f.id === file.folderId)?.path || ''}/${file.filename}`,
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

<div class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none">
  <div class="w-full max-w-4xl h-[80vh] bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="p-1.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
          <HardDrive class="w-4 h-4" />
        </div>
        <div>
          <h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Import from Corporate Drive
          </h2>
          <div class="text-[11px] text-neutral-400 dark:text-neutral-500">
            Target Collection: <strong class="text-neutral-700 dark:text-neutral-300">{collection.name}</strong>
          </div>
        </div>
      </div>

      <button
        type="button"
        onclick={onClose}
        class="p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 rounded transition-colors cursor-pointer"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Ingesting Progress Overlay -->
    {#if isIngesting}
      <div class="absolute inset-0 z-20 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center">
        <div class="w-12 h-12 rounded-full border-3 border-neutral-200 dark:border-neutral-700 border-t-neutral-900 dark:border-t-neutral-100 animate-spin mb-4"></div>
        <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Ingesting into Collection</h3>
        <p class="text-xs text-neutral-500 dark:text-neutral-400 font-mono mt-1 max-w-md">
          {ingestionStep}
        </p>
      </div>
    {/if}

    <!-- Main Drive Browser Split: Folders on Left, Files on Right -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Folders List -->
      <div class="w-64 bg-neutral-50 dark:bg-neutral-950 border-r border-neutral-200 dark:border-neutral-800 p-3 flex flex-col text-xs shrink-0">
        <div class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2 px-2">
          Folders
        </div>
        <div class="space-y-1">
          {#each DRIVE_FOLDERS.filter((f) => f.id !== 'f-root') as folder (folder.id)}
            {@const isSelected = selectedFolderId === folder.id}
            {@const fileCountInFolder = DRIVE_FILES.filter((f) => f.folderId === folder.id).length}

            <button
              type="button"
              onclick={() => {
                selectedFolderId = folder.id;
                searchQuery = '';
              }}
              class="w-full text-left px-2.5 py-2 rounded-md flex items-center justify-between transition-colors cursor-pointer {isSelected
                ? 'bg-blue-600 text-white font-medium shadow-2xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200/70 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-neutral-100'}"
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

        <div class="mt-auto p-2 rounded bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-500 dark:text-neutral-400">
          <span class="font-semibold text-neutral-700 dark:text-neutral-300 block mb-0.5">Automated Extraction</span>
          Files are automatically parsed, sliced into token chunks, and registered with page offsets.
        </div>
      </div>

      <!-- Files List View -->
      <div class="flex-1 flex flex-col overflow-hidden bg-white dark:bg-neutral-900">
        <!-- Search Filter Bar -->
        <div class="p-3 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-3">
          <div class="relative flex-1">
            <Search class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search files in Drive..."
              bind:value={searchQuery}
              class="w-full pl-8 pr-3 py-1.5 text-xs bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500"
            />
          </div>

          <div class="text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">
            {selectedFileIds.size} selected
          </div>
        </div>

        <!-- File Table -->
        <div class="flex-1 overflow-y-auto p-4 space-y-2">
          {#each visibleFiles as file (file.id)}
            {@const isSelected = selectedFileIds.has(file.id)}
            {@const isAlreadyIngested = existingDocTitles.includes(file.title)}

            <div
              role="button"
              tabindex="0"
              onclick={() => !isAlreadyIngested && toggleFileSelect(file.id)}
              onkeydown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && !isAlreadyIngested) toggleFileSelect(file.id); }}
              class="p-3 rounded-lg border text-xs transition-all flex items-start justify-between gap-3 {isAlreadyIngested
                ? 'opacity-50 bg-neutral-50 dark:bg-neutral-800/40 border-neutral-200 dark:border-neutral-800 cursor-not-allowed'
                : isSelected
                ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
                : 'bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 border-neutral-200 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100 cursor-pointer'}"
            >
              <div class="flex items-start gap-3 min-w-0">
                <div
                  class="w-4 h-4 rounded border mt-0.5 flex items-center justify-center shrink-0 {isSelected
                    ? 'bg-white border-white text-blue-600'
                    : 'border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800'}"
                >
                  {#if isSelected}
                    <Check class="w-3 h-3 stroke-3" />
                  {/if}
                </div>

                <div class="min-w-0">
                  <div class="font-semibold truncate flex items-center gap-2">
                    <span class={isSelected ? 'text-white' : 'text-neutral-900 dark:text-neutral-100'}>
                      {file.title}
                    </span>
                    {#if isAlreadyIngested}
                      <span class="text-[10px] text-neutral-400 dark:text-neutral-500 uppercase font-mono">
                        Already Ingested
                      </span>
                    {/if}
                  </div>

                  <p
                    class="text-[11px] mt-0.5 line-clamp-1 {isSelected ? 'text-blue-100' : 'text-neutral-500 dark:text-neutral-400'}"
                  >
                    {file.previewSummary}
                  </p>

                  <div
                    class="mt-1.5 flex items-center gap-2 text-[10px] font-mono tabular-nums {isSelected ? 'text-blue-200' : 'text-neutral-400 dark:text-neutral-500'}"
                  >
                    <span>{file.filename}</span>
                    <span aria-hidden="true">·</span>
                    <span>{(file.sizeBytes / (1024 * 1024)).toFixed(1)} MB</span>
                    <span aria-hidden="true">·</span>
                    <span>Author: {file.author}</span>
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="h-14 px-6 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="text-xs text-neutral-500 dark:text-neutral-400 font-mono tabular-nums flex items-center gap-2">
        <span>{selectedFileIds.size} file(s) selected</span>
        <span>·</span>
        <span class="text-blue-700 dark:text-blue-400 font-semibold font-sans">Quota: {collection.allocatedGb || 10} GB</span>
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
          <span>Import &amp; Ingest ({selectedFileIds.size})</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </div>
</div>
