<script lang="ts">
  import {
    ArrowLeft,
    FileText,
    Network,
    Upload,
    HardDrive,
    Search,
    Trash2,
    ExternalLink,
    ChevronRight,
    ArrowRight,
    LayoutList,
    LayoutGrid,
    Sliders,
    Lock
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, TeamAllocationRecord, UserProfile } from '../types';
  import DocumentGridCardPreview from './DocumentGridCardPreview.svelte';
  import CollectionVectorGraph from './CollectionVectorGraph.svelte';
  import { formatBytes, getCollectionUsedBytes } from '../utils/resourceUtils';
  import {
    canUploadToCollection,
    canDeleteDocument,
    canManageCollectionQuota,
    canDeleteCollection
  } from '../utils/governance';

  interface Props {
    collection: Collection;
    documents: DocumentItem[];
    collections?: Collection[];
    currentUser?: UserProfile;
    teamAllocations?: TeamAllocationRecord[];
    onOpenTeamAllocationModal?: (teamRecord: TeamAllocationRecord) => void;
    onBack: () => void;
    onOpenGraph?: () => void;
    onOpenUploadModal: () => void;
    onOpenDriveModal: () => void;
    onOpenDocument: (doc: DocumentItem, pageNumber?: number, chunkId?: string) => void;
    onDeleteDocument: (docId: string) => void;
    onDeleteCollection?: (col: Collection) => void;
  }

  let {
    collection,
    documents,
    collections = [],
    currentUser,
    teamAllocations,
    onOpenTeamAllocationModal,
    onBack,
    onOpenGraph,
    onOpenUploadModal,
    onOpenDriveModal,
    onOpenDocument,
    onDeleteDocument,
    onDeleteCollection,
  }: Props = $props();

  let activeTab = $state<'documents' | 'graph'>('documents');
  let docSearchQuery = $state('');
  let selectedDocId = $state<string | null>(null);
  let viewMode = $state<'list' | 'grid'>('list');

  let collectionDocs = $derived(documents.filter((doc) => doc.collectionId === collection.id));

  let usedBytes = $derived(getCollectionUsedBytes(collection.id, documents));
  let allocatedGb = $derived(collection.allocatedGb || (collection.scope === 'mine' ? 5 : 20));
  let allocatedBytes = $derived(allocatedGb * 1024 * 1024 * 1024);
  let usedPercent = $derived(Math.min(100, Math.round((usedBytes / Math.max(1, allocatedBytes)) * 100)));

  let targetTeam = $derived(
    teamAllocations?.find(
      (t) => t.teamName.toLowerCase() === (collection.teamName || '').toLowerCase()
    )
  );

  let canUpload = $derived(canUploadToCollection(currentUser, collection));
  let canManageQuota = $derived(canManageCollectionQuota(currentUser, collection));
  let canDelete = $derived(canDeleteCollection(currentUser, collection));

  let filteredDocs = $derived.by(() => {
    if (!docSearchQuery.trim()) return collectionDocs;
    const q = docSearchQuery.toLowerCase();
    return collectionDocs.filter(
      (doc) =>
        doc.title.toLowerCase().includes(q) ||
        doc.summary.toLowerCase().includes(q) ||
        doc.entities.some((e) => e.toLowerCase().includes(q))
    );
  });

  let scopeLabel = $derived(
    collection.scope === 'project'
      ? `Project (${collection.projectName || 'Active'})`
      : collection.scope === 'org'
      ? 'Organization'
      : `Team (${collection.teamName || 'Engineering'})`
  );
</script>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Header Bar -->
  <div class="min-h-14 py-2 px-3 sm:px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex flex-wrap items-center justify-between gap-2 shrink-0">
    <div class="flex items-center gap-1.5 sm:gap-2 text-xs min-w-0">
      <button
        type="button"
        onclick={onBack}
        class="flex items-center gap-1 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors cursor-pointer shrink-0"
      >
        <ArrowLeft class="w-4 h-4" />
        <span>Collections</span>
      </button>
      <ChevronRight class="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-700 shrink-0" />
      <span class="text-neutral-400 dark:text-neutral-500 truncate max-w-[80px] sm:max-w-none">{scopeLabel}</span>
      <ChevronRight class="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-700 shrink-0" />
      <span class="font-semibold text-neutral-900 dark:text-neutral-100 truncate max-w-[130px] sm:max-w-xs">{collection.name}</span>
    </div>

    <!-- Action Buttons -->
    <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
      {#if onOpenGraph}
        <button
          type="button"
          onclick={onOpenGraph}
          class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
          title="Open in Vector Knowledge Graph"
        >
          <Network class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
          <span class="hidden sm:inline">Explore in Graph</span>
          <span class="sm:hidden">Graph</span>
        </button>
      {/if}

      {#if canUpload}
        <button
          type="button"
          onclick={onOpenDriveModal}
          class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
        >
          <HardDrive class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span class="hidden sm:inline">Upload from Drive</span>
          <span class="sm:hidden">Drive</span>
        </button>

        <button
          type="button"
          onclick={onOpenUploadModal}
          class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <Upload class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">Upload Document</span>
          <span class="sm:hidden">Upload</span>
        </button>
      {:else}
        <div class="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-500 dark:text-neutral-400 text-xs rounded-md">
          <Lock class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
          <span>Read-Only Viewer</span>
        </div>
      {/if}

      {#if canDelete && collection.id !== 'all_knowledge_base'}
        <button
          type="button"
          onclick={() => onDeleteCollection?.(collection)}
          class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900/60 hover:bg-rose-100 dark:hover:bg-rose-900/60 text-rose-700 dark:text-rose-300 text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
          title="Delete this collection"
        >
          <Trash2 class="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
          <span class="hidden sm:inline">Delete Collection</span>
          <span class="sm:hidden">Delete</span>
        </button>
      {/if}
    </div>
  </div>

  <!-- Collection Header -->
  <div class="px-4 sm:px-6 py-3 sm:py-4 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 shrink-0">
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
      <div>
        <h1 class="text-base sm:text-lg font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight">
          {collection.name}
        </h1>
        <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 max-w-2xl leading-relaxed">
          {collection.description}
        </p>

        <div class="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500 mt-2">
          <span>{collectionDocs.length} documents</span>
          <span>·</span>
          <span>Created by {collection.createdBy.name}</span>
        </div>

        <!-- Storage Quota Bar -->
        <div class="mt-2.5 flex flex-wrap items-center gap-2.5 pt-2 border-t border-neutral-100 dark:border-neutral-800">
          <div class="flex items-center gap-2 text-xs">
            <span class="font-semibold text-neutral-700 dark:text-neutral-300 flex items-center gap-1">
              <HardDrive class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>Storage Quota:</span>
            </span>
            <span class="font-mono text-neutral-600 dark:text-neutral-400 text-[11px] sm:text-xs">
              <strong class="text-neutral-900 dark:text-neutral-100">{formatBytes(usedBytes)}</strong> / {allocatedGb} GB used ({usedPercent}%)
            </span>
          </div>

          <div class="w-24 sm:w-28 h-2 bg-neutral-100 dark:bg-neutral-700 rounded-full overflow-hidden border border-neutral-200 dark:border-neutral-600">
            <div
              class="h-full transition-all duration-300 {usedPercent > 90 ? 'bg-rose-500' : 'bg-blue-600'}"
              style="width: {Math.max(2, usedPercent)}%"
            ></div>
          </div>

          {#if collection.scope === 'team' && targetTeam && onOpenTeamAllocationModal && canManageQuota}
            <button
              type="button"
              onclick={() => onOpenTeamAllocationModal(targetTeam)}
              class="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 sm:ml-auto cursor-pointer"
            >
              <Sliders class="w-3 h-3" />
              <span>Manage Team Quotas ({targetTeam.teamName})</span>
            </button>
          {/if}
        </div>
      </div>

      <!-- Simple Tab Switcher -->
      <div class="flex items-center p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 shrink-0">
        <button
          type="button"
          onclick={() => (activeTab = 'documents')}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer {activeTab === 'documents'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        >
          <FileText class="w-3.5 h-3.5" />
          <span>Documents ({collectionDocs.length})</span>
        </button>

        <button
          type="button"
          onclick={() => (activeTab = 'graph')}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer {activeTab === 'graph'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        >
          <Network class="w-3.5 h-3.5" />
          <span>Related Documents</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Content Area -->
  {#if activeTab === 'documents'}
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Search bar & View Mode Switcher inside collection -->
      <div class="px-3 sm:px-6 py-2 bg-neutral-100/70 dark:bg-neutral-900/60 border-b border-neutral-200 dark:border-neutral-800 flex flex-wrap items-center justify-between gap-2.5 shrink-0">
        <div class="relative flex-1 sm:flex-initial min-w-[180px]">
          <Search class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter documents..."
            bind:value={docSearchQuery}
            class="pl-8 pr-3 py-1 text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500 w-full sm:w-64"
          />
        </div>

        <div class="flex items-center gap-2.5 sm:gap-3">
          <span class="text-xs text-neutral-500 dark:text-neutral-400 font-medium">
            {filteredDocs.length} {filteredDocs.length === 1 ? 'file' : 'files'}
          </span>

          <!-- View Format Switcher -->
          <div class="flex items-center gap-1 text-xs">
            <span class="text-neutral-500 dark:text-neutral-400 font-medium text-[11px] hidden sm:inline">Format:</span>
            <div class="flex items-center p-0.5 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
              <button
                type="button"
                onclick={() => (viewMode = 'list')}
                class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-md text-xs transition-colors cursor-pointer {viewMode === 'list'
                  ? 'bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                title="View files in table list format"
              >
                <LayoutList class="w-3.5 h-3.5" />
                <span>List</span>
              </button>
              <button
                type="button"
                onclick={() => (viewMode = 'grid')}
                class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-md text-xs transition-colors cursor-pointer {viewMode === 'grid'
                  ? 'bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                title="View files as visual preview boxes"
              >
                <LayoutGrid class="w-3.5 h-3.5" />
                <span>Preview</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Document Content: List Table or Enterprise Preview Boxes -->
      <div class="flex-1 overflow-y-auto p-3 sm:p-6 custom-scrollbar">
        {#if filteredDocs.length === 0}
          <div class="h-60 border border-dashed border-neutral-300 dark:border-neutral-800 rounded-lg flex flex-col items-center justify-center text-center p-6 bg-white dark:bg-neutral-900">
            <FileText class="w-8 h-8 text-neutral-300 dark:text-neutral-600 mb-2" />
            <h3 class="text-sm font-semibold text-neutral-800 dark:text-neutral-200">No documents in this collection</h3>
            <p class="text-xs text-neutral-500 dark:text-neutral-400 max-w-sm mt-1 mb-4">
              Add files to this collection to enable semantic search and cross-referencing.
            </p>
            {#if canUpload}
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={onOpenUploadModal}
                  class="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 cursor-pointer shadow-xs"
                >
                  Upload Document
                </button>
                <button
                  type="button"
                  onclick={onOpenDriveModal}
                  class="px-3 py-1.5 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 text-xs font-medium rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700 cursor-pointer"
                >
                  Upload from Drive
                </button>
              </div>
            {/if}
          </div>
        {:else if viewMode === 'list'}
          <div class="bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 overflow-x-auto custom-scrollbar shadow-2xs">
            <table class="w-full min-w-[620px] md:min-w-full text-left text-xs">
              <thead class="bg-neutral-50 dark:bg-neutral-800/60 border-b border-neutral-200 dark:border-neutral-800 text-neutral-500 dark:text-neutral-400 font-medium">
                <tr>
                  <th class="py-2.5 px-3 sm:px-4">Document Title</th>
                  <th class="py-2.5 px-2 sm:px-3">Status</th>
                  <th class="py-2.5 px-2 sm:px-3 hidden md:table-cell">Source</th>
                  <th class="py-2.5 px-2 sm:px-3 text-right hidden sm:table-cell">Size</th>
                  <th class="py-2.5 px-2 sm:px-3 hidden lg:table-cell">Date Added</th>
                  <th class="py-2.5 px-2 sm:px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 dark:divide-neutral-800">
                {#each filteredDocs as doc (doc.id)}
                  <tr
                    class="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors group cursor-pointer"
                    onclick={() => onOpenDocument(doc, 1)}
                  >
                    <td class="py-2.5 px-3 sm:px-4 max-w-[170px] sm:max-w-xs md:max-w-sm lg:max-w-md">
                      <div class="flex items-start gap-2 sm:gap-2.5 min-w-0">
                        <span class="p-1 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 font-mono text-[10px] uppercase font-semibold mt-0.5 shrink-0">
                          {doc.fileType}
                        </span>
                        <div class="min-w-0 flex-1">
                          <div class="flex items-center gap-2">
                            <span
                              class="font-semibold text-neutral-900 dark:text-neutral-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate text-xs sm:text-sm"
                              title={doc.title}
                            >
                              {doc.title}
                            </span>
                            <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-500 border border-neutral-200 dark:border-neutral-700">
                              {doc.id}
                            </span>
                            {#if doc.visibility === 'private'}
                              <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-0.5">
                                <Lock class="w-2.5 h-2.5" />
                                <span>Private</span>
                              </span>
                            {:else}
                              <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                                Shared
                              </span>
                            {/if}
                          </div>
                          <div
                            class="text-[11px] text-neutral-500 dark:text-neutral-400 truncate mt-0.5"
                            title={doc.summary}
                          >
                            {doc.summary}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td class="py-2.5 px-2 sm:px-3 whitespace-nowrap">
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] sm:text-[11px] font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
                        <span class="hidden sm:inline">Ingested ({doc.chunkCount} chunks)</span>
                        <span class="sm:hidden">Ingested ({doc.chunkCount}c)</span>
                      </span>
                    </td>

                    <td class="py-2.5 px-2 sm:px-3 text-neutral-600 dark:text-neutral-400 whitespace-nowrap hidden md:table-cell">
                      <div>
                        <span class="font-medium text-[11px] text-neutral-700 dark:text-neutral-300">
                          {doc.source === 'drive' ? 'Corporate Drive' : 'Direct Upload'}
                        </span>
                        {#if doc.drivePath}
                          <span class="block text-[10px] text-neutral-400 dark:text-neutral-500 font-mono truncate max-w-[160px]" title={doc.drivePath}>
                            {doc.drivePath}
                          </span>
                        {/if}
                      </div>
                    </td>

                    <td class="py-2.5 px-2 sm:px-3 text-right font-mono tabular-nums text-neutral-600 dark:text-neutral-300 hidden sm:table-cell">
                      {formatBytes(doc.sizeBytes)}
                    </td>

                    <td class="py-2.5 px-2 sm:px-3 text-neutral-500 dark:text-neutral-400 whitespace-nowrap hidden lg:table-cell">
                      {new Date(doc.uploadedAt).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </td>

                    <td class="py-2.5 px-2 sm:px-4 text-right whitespace-nowrap" onclick={(e) => e.stopPropagation()}>
                      <div class="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onclick={() => onOpenDocument(doc, 1)}
                          class="px-2 sm:px-2.5 py-1 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded transition-colors flex items-center gap-1 cursor-pointer"
                        >
                          <span>Open</span>
                          <ExternalLink class="w-3 h-3" />
                        </button>

                        {#if canDeleteDocument(currentUser, doc, collection)}
                          <button
                            type="button"
                            onclick={() => onDeleteDocument(doc.id)}
                            class="p-1 text-neutral-400 dark:text-neutral-500 hover:text-rose-600 dark:hover:text-rose-400 rounded transition-colors cursor-pointer"
                            title="Delete"
                          >
                            <Trash2 class="w-3.5 h-3.5" />
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <!-- Google Drive Style Grid View (Compact, Uncluttered, Minimalist) -->
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {#each filteredDocs as doc (doc.id)}
              <div class="relative group">
                <DocumentGridCardPreview
                  {doc}
                  onclick={() => onOpenDocument(doc, 1)}
                />
                {#if canDeleteDocument(currentUser, doc, collection)}
                  <button
                    type="button"
                    onclick={(e) => {
                      e.stopPropagation();
                      onDeleteDocument(doc.id);
                    }}
                    class="absolute top-2 right-2 p-1.5 rounded-md bg-white/95 dark:bg-neutral-900/95 text-neutral-400 hover:text-rose-600 dark:hover:text-rose-400 border border-neutral-200 dark:border-neutral-700 shadow-xs opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer z-10"
                    title="Remove from collection"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <!-- Related Documents View: Interactive Document-Only Vector Knowledge Graph -->
    <div class="flex-1 overflow-hidden flex flex-col">
      <CollectionVectorGraph
        {collection}
        allDocuments={documents}
        {collections}
        {currentUser}
        {selectedDocId}
        {onOpenDocument}
      />
    </div>
  {/if}
</div>
