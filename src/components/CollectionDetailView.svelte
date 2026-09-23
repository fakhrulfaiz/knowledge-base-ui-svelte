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
  import { computeDocumentGraph } from '../utils/retrieval';
  import DocumentGridCardPreview from './DocumentGridCardPreview.svelte';
  import { formatBytes, getCollectionUsedBytes } from '../utils/resourceUtils';
  import {
    canUploadToCollection,
    canDeleteDocument,
    canManageCollectionQuota
  } from '../utils/governance';

  interface Props {
    collection: Collection;
    documents: DocumentItem[];
    currentUser?: UserProfile;
    teamAllocations?: TeamAllocationRecord[];
    onOpenTeamAllocationModal?: (teamRecord: TeamAllocationRecord) => void;
    onBack: () => void;
    onOpenUploadModal: () => void;
    onOpenDriveModal: () => void;
    onOpenDocument: (doc: DocumentItem, pageNumber?: number, chunkId?: string) => void;
    onDeleteDocument: (docId: string) => void;
  }

  let {
    collection,
    documents,
    currentUser,
    teamAllocations,
    onOpenTeamAllocationModal,
    onBack,
    onOpenUploadModal,
    onOpenDriveModal,
    onOpenDocument,
    onDeleteDocument,
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

  let graph = $derived(computeDocumentGraph(collectionDocs, 'combined', 0.15));

  let scopeLabel = $derived(
    collection.scope === 'mine'
      ? 'My Collections'
      : collection.scope === 'org'
      ? 'Organization'
      : `Team (${collection.teamName || 'Engineering'})`
  );

  let activeFocusDoc = $derived(
    collectionDocs.find((d) => d.id === selectedDocId) || collectionDocs[0] || null
  );

  let relatedEdges = $derived.by(() => {
    if (!activeFocusDoc) return [];
    return graph.edges.filter(
      (e) => e.source === activeFocusDoc.id || e.target === activeFocusDoc.id
    );
  });
</script>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Header Bar -->
  <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-2 text-xs">
      <button
        type="button"
        onclick={onBack}
        class="flex items-center gap-1 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors cursor-pointer"
      >
        <ArrowLeft class="w-4 h-4" />
        <span>Collections</span>
      </button>
      <ChevronRight class="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-700" />
      <span class="text-neutral-400 dark:text-neutral-500">{scopeLabel}</span>
      <ChevronRight class="w-3.5 h-3.5 text-neutral-300 dark:text-neutral-700" />
      <span class="font-semibold text-neutral-900 dark:text-neutral-100 truncate max-w-xs">{collection.name}</span>
    </div>

    <!-- Action Buttons -->
    <div class="flex items-center gap-2">
      {#if canUpload}
        <button
          type="button"
          onclick={onOpenDriveModal}
          class="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
        >
          <HardDrive class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>Import from Drive</span>
        </button>

        <button
          type="button"
          onclick={onOpenUploadModal}
          class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <Upload class="w-3.5 h-3.5" />
          <span>Upload Document</span>
        </button>
      {:else}
        <div class="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-500 dark:text-neutral-400 text-xs rounded-md">
          <Lock class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
          <span>Read-Only Viewer</span>
        </div>
      {/if}
    </div>
  </div>

  <!-- Collection Header -->
  <div class="px-6 py-4 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 shrink-0">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight">
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
        <div class="mt-3 flex flex-wrap items-center gap-3 pt-2 border-t border-neutral-100 dark:border-neutral-800">
          <div class="flex items-center gap-2 text-xs">
            <span class="font-semibold text-neutral-700 dark:text-neutral-300 flex items-center gap-1">
              <HardDrive class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>Storage Quota:</span>
            </span>
            <span class="font-mono text-neutral-600 dark:text-neutral-400">
              <strong class="text-neutral-900 dark:text-neutral-100">{formatBytes(usedBytes)}</strong> / {allocatedGb} GB used ({usedPercent}%)
            </span>
          </div>

          <div class="w-28 h-2 bg-neutral-100 dark:bg-neutral-700 rounded-full overflow-hidden border border-neutral-200 dark:border-neutral-600">
            <div
              class="h-full transition-all duration-300 {usedPercent > 90 ? 'bg-rose-500' : 'bg-blue-600'}"
              style="width: {Math.max(2, usedPercent)}%"
            ></div>
          </div>

          {#if collection.scope === 'team' && targetTeam && onOpenTeamAllocationModal && canManageQuota}
            <button
              type="button"
              onclick={() => onOpenTeamAllocationModal(targetTeam)}
              class="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 ml-auto cursor-pointer"
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
      <div class="px-6 py-2.5 bg-neutral-100/70 dark:bg-neutral-900/60 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-4 shrink-0">
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter documents..."
            bind:value={docSearchQuery}
            class="pl-8 pr-3 py-1 text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500 w-64"
          />
        </div>

        <div class="flex items-center gap-3">
          <span class="text-xs text-neutral-500 dark:text-neutral-400 font-medium">
            {filteredDocs.length} {filteredDocs.length === 1 ? 'file' : 'files'}
          </span>

          <!-- View Format Switcher -->
          <div class="flex items-center gap-1.5 text-xs">
            <span class="text-neutral-500 dark:text-neutral-400 font-medium text-[11px]">Format:</span>
            <div class="flex items-center p-0.5 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
              <button
                type="button"
                onclick={() => (viewMode = 'list')}
                class="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs transition-colors cursor-pointer {viewMode === 'list'
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
                class="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs transition-colors cursor-pointer {viewMode === 'grid'
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
      <div class="flex-1 overflow-y-auto p-6">
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
                  Import from Drive
                </button>
              </div>
            {/if}
          </div>
        {:else if viewMode === 'list'}
          <div class="bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 overflow-hidden shadow-2xs">
            <table class="w-full text-left text-xs">
              <thead class="bg-neutral-50 dark:bg-neutral-800/60 border-b border-neutral-200 dark:border-neutral-800 text-neutral-500 dark:text-neutral-400 font-medium">
                <tr>
                  <th class="py-2.5 px-4">Document Title</th>
                  <th class="py-2.5 px-3">Format</th>
                  <th class="py-2.5 px-3">Source</th>
                  <th class="py-2.5 px-3 text-right">Size</th>
                  <th class="py-2.5 px-3">Date Added</th>
                  <th class="py-2.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 dark:divide-neutral-800">
                {#each filteredDocs as doc (doc.id)}
                  <tr
                    class="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors group cursor-pointer"
                    onclick={() => onOpenDocument(doc, 1)}
                  >
                    <td class="py-3 px-4">
                      <div class="flex items-start gap-2.5">
                        <span class="p-1 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 font-mono text-[10px] uppercase font-semibold mt-0.5">
                          {doc.fileType}
                        </span>
                        <div class="min-w-0">
                          <div class="font-semibold text-neutral-900 dark:text-neutral-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-1 text-sm">
                            {doc.title}
                          </div>
                          <div class="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-1 mt-0.5">
                            {doc.summary}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td class="py-3 px-3 text-neutral-600 dark:text-neutral-400 uppercase font-mono text-[11px] whitespace-nowrap">
                      {doc.fileType}
                    </td>

                    <td class="py-3 px-3 text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
                      {doc.source === 'drive' ? 'Google Drive' : 'Direct Upload'}
                    </td>

                    <td class="py-3 px-3 text-right font-mono tabular-nums text-neutral-600 dark:text-neutral-300">
                      {formatBytes(doc.sizeBytes)}
                    </td>

                    <td class="py-3 px-3 text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
                      {new Date(doc.uploadedAt).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </td>

                    <td class="py-3 px-4 text-right whitespace-nowrap" onclick={(e) => e.stopPropagation()}>
                      <div class="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onclick={() => onOpenDocument(doc, 1)}
                          class="px-2.5 py-1 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded transition-colors flex items-center gap-1 cursor-pointer"
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
          <!-- Grid View with Enterprise Document Preview Boxes -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {#each filteredDocs as doc (doc.id)}
              {@const firstPageText = doc.pages[0]?.chunks[0]?.snippet || doc.summary}
              <div
                role="button"
                tabindex="0"
                onclick={() => onOpenDocument(doc, 1)}
                onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onOpenDocument(doc, 1); }}
                class="bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 hover:border-neutral-400 dark:hover:border-neutral-600 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group overflow-hidden"
              >
                <!-- Enterprise Document Box Preview -->
                <DocumentGridCardPreview
                  title={doc.title}
                  fileType={doc.fileType}
                  pageCount={doc.pageCount}
                  firstPageSnippet={firstPageText}
                />

                <!-- Card Content Footer -->
                <div class="p-4 space-y-3 bg-white dark:bg-neutral-900 flex-1 flex flex-col justify-between">
                  <div>
                    <div class="flex items-center justify-between text-xs text-neutral-400 dark:text-neutral-500 mb-1.5">
                      <span class="font-mono font-semibold text-neutral-600 dark:text-neutral-300 uppercase">
                        {doc.fileType}
                      </span>
                      <span class="font-mono">{formatBytes(doc.sizeBytes)}</span>
                    </div>
                    <h4 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 line-clamp-2 transition-colors">
                      {doc.title}
                    </h4>
                    <p class="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 mt-1.5 leading-relaxed">
                      {doc.summary}
                    </p>
                  </div>

                  <div class="pt-3 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
                    <span class="text-[11px] text-neutral-400 dark:text-neutral-500">
                      Added {new Date(doc.uploadedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-neutral-100 dark:bg-neutral-800 group-hover:bg-blue-600 group-hover:text-white text-neutral-700 dark:text-neutral-200 text-xs font-semibold transition-colors">
                      <span>Open Document</span>
                      <ExternalLink class="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <!-- Related Documents View: Clean, intuitive visual connection -->
    <div class="flex-1 flex overflow-hidden bg-neutral-50 dark:bg-neutral-950">
      <!-- Document list on left -->
      <div class="w-80 bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800 flex flex-col shrink-0">
        <div class="p-3 border-b border-neutral-200 dark:border-neutral-800 text-xs font-medium text-neutral-500 dark:text-neutral-400">
          Select Document to Inspect Connections
        </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-1">
          {#each collectionDocs as doc (doc.id)}
            {@const isSelected = activeFocusDoc?.id === doc.id}
            {@const docConnectionsCount = graph.edges.filter(
              (e) => e.source === doc.id || e.target === doc.id
            ).length}
            <button
              type="button"
              onclick={() => (selectedDocId = doc.id)}
              class="w-full text-left p-2.5 rounded-lg border text-xs transition-all cursor-pointer {isSelected
                ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                : 'bg-white dark:bg-neutral-800/60 hover:bg-neutral-100 dark:hover:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200'}"
            >
              <div class="font-semibold line-clamp-1">{doc.title}</div>
              <div
                class="text-[11px] mt-1 flex items-center justify-between {isSelected
                  ? 'text-blue-100'
                  : 'text-neutral-400 dark:text-neutral-500'}"
              >
                <span>{doc.pageCount} pages</span>
                <span>{docConnectionsCount} connections</span>
              </div>
            </button>
          {/each}
        </div>
      </div>

      <!-- Right Connections Details -->
      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        {#if activeFocusDoc}
          <div>
            <div class="bg-white dark:bg-neutral-900 p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-2xs space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-[10px] uppercase font-mono tracking-wider text-neutral-400 dark:text-neutral-500">
                  Currently Focused Document
                </span>
                <button
                  type="button"
                  onclick={() => onOpenDocument(activeFocusDoc, 1)}
                  class="flex items-center gap-1 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 cursor-pointer"
                >
                  <span>Open Document</span>
                  <ExternalLink class="w-3 h-3" />
                </button>
              </div>
              <h2 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                {activeFocusDoc.title}
              </h2>
              <p class="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
                {activeFocusDoc.summary}
              </p>
              {#if activeFocusDoc.entities.length > 0}
                <div class="pt-2 border-t border-neutral-100 dark:border-neutral-800 flex flex-wrap gap-1.5">
                  {#each activeFocusDoc.entities as e, idx (idx)}
                    <span
                      class="px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 text-[11px]"
                    >
                      {e}
                    </span>
                  {/each}
                </div>
              {/if}
            </div>

            <!-- Connected Documents List -->
            <div class="mt-6 space-y-3">
              <h3 class="text-xs font-semibold text-neutral-700 dark:text-neutral-300 uppercase tracking-wider">
                Connected Documents in Collection ({relatedEdges.length})
              </h3>

              {#if relatedEdges.length === 0}
                <div class="p-6 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg text-center text-xs text-neutral-400 dark:text-neutral-500">
                  No strong direct correlations found for this document yet. Add more related files to establish cross-references.
                </div>
              {:else}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {#each relatedEdges as edge, i (i)}
                    {@const targetId = edge.source === activeFocusDoc.id ? edge.target : edge.source}
                    {@const targetDoc = collectionDocs.find((d) => d.id === targetId)}
                    {#if targetDoc}
                      <div
                        class="p-4 bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div class="flex items-center justify-between text-[11px] text-neutral-400 dark:text-neutral-500 mb-1">
                            <span class="text-neutral-600 dark:text-neutral-300 font-medium">
                              {Math.round(edge.weight * 100)}% relationship match
                            </span>
                            <span class="uppercase text-[10px] font-mono">
                              {edge.type}
                            </span>
                          </div>

                          <h4 class="text-xs font-semibold text-neutral-900 dark:text-neutral-100 line-clamp-1 mb-1.5">
                            {targetDoc.title}
                          </h4>

                          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-800/60 p-2 rounded border border-neutral-100 dark:border-neutral-800 mb-2">
                            {edge.reasons[0] || 'Shared architecture & technical scope'}
                          </div>
                        </div>

                        <button
                          type="button"
                          onclick={() => onOpenDocument(targetDoc, 1)}
                          class="mt-2 flex items-center justify-between text-xs text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 font-medium pt-2 border-t border-neutral-100 dark:border-neutral-800 cursor-pointer"
                        >
                          <span>Read Connected Doc</span>
                          <ArrowRight class="w-3 h-3" />
                        </button>
                      </div>
                    {/if}
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        {:else}
          <div class="text-center text-neutral-400 dark:text-neutral-500 text-xs py-12">
            No documents found in this collection.
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
