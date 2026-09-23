<script lang="ts">
  import {
    Folder,
    MoreVertical,
    ChevronDown,
    ChevronRight,
    Info,
    Search,
    FolderKanban,
    FileText,
    Sparkles,
    Shield,
    HardDrive,
    X
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, UserProfile } from '../types';
  import DocumentGridCardPreview from './DocumentGridCardPreview.svelte';

  interface Props {
    currentUser: UserProfile;
    collections: Collection[];
    documents: DocumentItem[];
    onSelectCollection: (id: string) => void;
    onOpenDocument: (doc: DocumentItem, pageNumber?: number) => void;
    onNavigate: (view: 'collections' | 'search') => void;
    onOpenNewCollection?: () => void;
  }

  let {
    currentUser,
    collections,
    documents,
    onSelectCollection,
    onOpenDocument,
    onNavigate,
    onOpenNewCollection,
  }: Props = $props();

  let isSuggestedCollectionsOpen = $state(true);
  let isSuggestedFilesOpen = $state(true);
  let showInfoModal = $state(false);

  // Suggested collections: prioritize collections with documents
  let suggestedCollections = $derived(
    [...collections]
      .sort((a, b) => b.documentCount - a.documentCount || new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, 5)
  );

  // Suggested / Recent files: most recently uploaded
  let recentFiles = $derived(
    [...documents]
      .sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())
      .slice(0, 12)
  );
</script>

<div class="flex-1 flex flex-col h-screen overflow-y-auto bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Navigation & Welcome Header -->
  <div class="px-8 pt-7 pb-4 flex items-center justify-between shrink-0">
    <h1 class="text-2xl font-normal text-neutral-900 dark:text-neutral-100 font-sans tracking-tight">
      Welcome to Cognify Knowledge Base
    </h1>

    <div class="flex items-center gap-2">
      <button
        type="button"
        onclick={() => (showInfoModal = !showInfoModal)}
        class="p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-600 dark:text-neutral-400 transition-colors cursor-pointer"
        title="Knowledge Base Info & Quick Stats"
        aria-label="Info"
      >
        <Info class="w-5 h-5" />
      </button>
    </div>
  </div>

  <!-- Main Body Sections -->
  <div class="px-8 pb-12 space-y-7">
    <!-- SECTION 1: Suggested Collections (Google Drive Capsule Row) -->
    <div class="space-y-3">
      <!-- Section Toggle Header -->
      <button
        type="button"
        onclick={() => (isSuggestedCollectionsOpen = !isSuggestedCollectionsOpen)}
        class="flex items-center gap-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 cursor-pointer select-none"
      >
        {#if isSuggestedCollectionsOpen}
          <ChevronDown class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
        {:else}
          <ChevronRight class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
        {/if}
        <span class="text-sm font-medium">Suggested collections</span>
      </button>

      {#if isSuggestedCollectionsOpen}
        <!-- Horizontal Capsule Grid / Scroll -->
        <div class="flex items-center gap-3 overflow-x-auto pb-1 scrollbar-none flex-wrap sm:flex-nowrap">
          {#each suggestedCollections as col (col.id)}
            <div
              role="button"
              tabindex="0"
              onclick={() => onSelectCollection(col.id)}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelectCollection(col.id);
              }}
              class="px-4 py-3 bg-[#f0f4f9] hover:bg-[#e4ebf5] dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-2xl flex items-center justify-between gap-3 cursor-pointer transition-all min-w-[210px] max-w-[260px] flex-1 shrink-0 border border-neutral-200/40 dark:border-neutral-700/60 shadow-2xs group"
              title="{col.name} ({col.documentCount} documents)"
            >
              <div class="flex items-center gap-3 min-w-0">
                <!-- Folder Icon Container -->
                <div class="w-8 h-8 rounded-lg bg-neutral-200/90 dark:bg-neutral-700 flex items-center justify-center text-neutral-700 dark:text-neutral-200 shrink-0">
                  <Folder class="w-4 h-4 fill-neutral-600 dark:fill-neutral-300 text-neutral-600 dark:text-neutral-300" />
                </div>

                <div class="min-w-0">
                  <div class="text-xs font-medium text-neutral-900 dark:text-neutral-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {col.name}
                  </div>
                  <div class="text-[11px] text-neutral-500 dark:text-neutral-400 truncate">
                    {col.scope === 'org' ? 'in Organization' : col.scope === 'team' ? `in ${col.teamName || 'Team'}` : 'in Personal'}
                  </div>
                </div>
              </div>

              <!-- More Options Icon -->
              <div class="p-1 rounded-full text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-200 transition-colors shrink-0">
                <MoreVertical class="w-3.5 h-3.5" />
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- SECTION 2: Suggested Files (Google Drive Compact Raster Grid) -->
    <div class="space-y-3 pt-2">
      <!-- Section Toggle Header -->
      <button
        type="button"
        onclick={() => (isSuggestedFilesOpen = !isSuggestedFilesOpen)}
        class="flex items-center gap-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 cursor-pointer select-none"
      >
        {#if isSuggestedFilesOpen}
          <ChevronDown class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
        {:else}
          <ChevronRight class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
        {/if}
        <span class="text-sm font-medium">Suggested files</span>
      </button>

      {#if isSuggestedFilesOpen}
        <!-- Responsive Google Drive Minimalist Cards Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {#each recentFiles as doc (doc.id)}
            <DocumentGridCardPreview
              {doc}
              onclick={() => onOpenDocument(doc, 1)}
            />
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- Info Drawer / Modal -->
{#if showInfoModal}
  <div class="fixed inset-0 z-50 bg-neutral-900/40 backdrop-blur-2xs flex items-center justify-center p-4">
    <div class="bg-white dark:bg-neutral-900 rounded-2xl shadow-xl border border-neutral-200 dark:border-neutral-800 w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150 text-neutral-900 dark:text-neutral-100">
      <div class="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-800 pb-3">
        <div class="flex items-center gap-2">
          <div class="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/70 text-blue-600 dark:text-blue-400">
            <Sparkles class="w-4 h-4" />
          </div>
          <h2 class="text-base font-semibold">About Cognify Knowledge Base</h2>
        </div>
        <button
          type="button"
          onclick={() => (showInfoModal = false)}
          class="p-1 rounded-md text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <p class="text-xs text-neutral-600 dark:text-neutral-300 leading-relaxed">
        Cognify is an enterprise-grade AI knowledge repository offering citation-backed passage retrieval, Google Drive synchronization, and role-based access governance.
      </p>

      <div class="grid grid-cols-2 gap-3 pt-1">
        <div class="p-3 bg-neutral-50 dark:bg-neutral-800/60 rounded-xl border border-neutral-200/80 dark:border-neutral-700/80">
          <div class="text-[11px] text-neutral-400 dark:text-neutral-500">Total Collections</div>
          <div class="text-lg font-bold text-neutral-900 dark:text-neutral-100 font-mono mt-0.5">
            {collections.length}
          </div>
        </div>

        <div class="p-3 bg-neutral-50 dark:bg-neutral-800/60 rounded-xl border border-neutral-200/80 dark:border-neutral-700/80">
          <div class="text-[11px] text-neutral-400 dark:text-neutral-500">Indexed Documents</div>
          <div class="text-lg font-bold text-neutral-900 dark:text-neutral-100 font-mono mt-0.5">
            {documents.length}
          </div>
        </div>
      </div>

      <div class="pt-2 flex justify-end">
        <button
          type="button"
          onclick={() => (showInfoModal = false)}
          class="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 dark:bg-neutral-100 dark:hover:bg-white text-white dark:text-neutral-900 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
        >
          Got it
        </button>
      </div>
    </div>
  </div>
{/if}
