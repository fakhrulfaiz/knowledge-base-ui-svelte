<script lang="ts">
  import {
    Search,
    FileText,
    ArrowRight,
    Bookmark,
    ExternalLink,
    User,
    Users,
    Building2,
    Sparkles,
    Tag,
    HardDrive,
    Layers,
    Clock,
    Hash
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, DocumentPage } from '../types';
  import { executeChunkSearch } from '../utils/retrieval';
  import { SAMPLE_SEARCH_QUERIES } from '../data/mockData';
  import HighlightedSnippet from './HighlightedSnippet.svelte';
  import PdfPageThumbnail from './PdfPageThumbnail.svelte';

  interface Props {
    documents: DocumentItem[];
    collections: Collection[];
    onOpenCitation: (doc: DocumentItem, pageNumber: number, chunkId: string) => void;
  }

  let { documents, collections, onOpenCitation }: Props = $props();

  let query = $state('Zero Trust mTLS architecture');
  let scope = $state<'all' | 'mine' | 'team' | 'org'>('all');
  let selectedCollectionId = $state<string>('all');
  let resultLimit = $state<number>(10);
  let selectedChunkId = $state<string | null>(null);

  let searchExecution = $derived(
    executeChunkSearch(
      {
        query,
        scope,
        collectionId: selectedCollectionId,
        topK: resultLimit,
        minScoreThreshold: 0.15,
      },
      documents,
      collections
    )
  );

  let results = $derived(searchExecution.results);
  let durationMs = $derived(searchExecution.durationMs);

  // Automatically select the top result if current selection is invalid or null
  let activeResult = $derived(
    results.find((r) => r.chunk.id === selectedChunkId) || results[0] || null
  );

  let activePage = $derived<DocumentPage | undefined>(
    activeResult?.document.pages.find(
      (p) => p.pageNumber === activeResult.chunk.pageNumber
    )
  );

  function handleSelectChunk(chunkId: string) {
    selectedChunkId = chunkId;
  }
</script>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Header Bar -->
  <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-2.5">
      <div class="p-1.5 rounded-md bg-blue-50 dark:bg-blue-950/70 text-blue-600 dark:text-blue-400">
        <Search class="w-4 h-4" />
      </div>
      <div>
        <h1 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Semantic Passage Search</h1>
      </div>
    </div>

    <div class="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400 font-mono">
      <span>{documents.length} docs indexed</span>
      <span>·</span>
      <span class="text-emerald-600 dark:text-emerald-400 font-medium">
        {results.length} matches ({durationMs}ms)
      </span>
    </div>
  </div>

  <!-- Search Input & Filters Strip -->
  <div class="px-6 py-4 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 shrink-0 space-y-3">
    <!-- Main Search Input -->
    <div class="relative max-w-4xl">
      <Search class="w-4 h-4 text-neutral-400 dark:text-neutral-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      <input
        type="text"
        bind:value={query}
        placeholder="Search questions, policies, specifications, and architecture decisions..."
        class="w-full pl-10 pr-16 py-2.5 bg-neutral-100/80 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-800/90 focus:bg-white dark:focus:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs md:text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-blue-500 dark:focus:border-blue-500 transition-all shadow-2xs"
      />
      {#if query}
        <button
          type="button"
          onclick={() => (query = '')}
          class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 text-xs px-2 py-0.5 rounded cursor-pointer"
        >
          Clear
        </button>
      {/if}
    </div>

    <!-- Quick Query Suggestions & Inline Scope Filters -->
    <div class="flex items-center justify-between flex-wrap gap-2 text-xs">
      <!-- Quick suggestions -->
      <div class="flex items-center gap-1.5 overflow-x-auto scrollbar-none py-0.5">
        <span class="text-[11px] text-neutral-400 dark:text-neutral-500 shrink-0 flex items-center gap-1">
          <Sparkles class="w-3 h-3 text-amber-500" />
          <span>Try:</span>
        </span>
        {#each SAMPLE_SEARCH_QUERIES as sample, idx (idx)}
          <button
            type="button"
            onclick={() => (query = sample)}
            class="px-2.5 py-1 rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-600 dark:text-neutral-300 text-[11px] transition-colors cursor-pointer shrink-0 truncate max-w-xs"
          >
            {sample}
          </button>
        {/each}
      </div>

      <!-- Scope Filters, Chunks Depth & Collection Select -->
      <div class="flex items-center gap-3 ml-auto flex-wrap sm:flex-nowrap">
        <!-- Chunks Limit Selector -->
        <div class="flex items-center gap-1.5 text-[11px]">
          <span class="text-neutral-500 dark:text-neutral-400 font-medium">Chunks:</span>
          <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700">
            {#each [10, 30, 50] as count}
              <button
                type="button"
                onclick={() => (resultLimit = count)}
                class="px-2 py-0.5 rounded text-[11px] font-mono transition-colors cursor-pointer {resultLimit === count
                  ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                title="Retrieve top {count} chunks"
              >
                {count}
              </button>
            {/each}
          </div>
        </div>

        <!-- Scope Segmented Control -->
        <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700 text-[11px]">
          <button
            type="button"
            onclick={() => (scope = 'all')}
            class="px-2 py-1 rounded transition-colors cursor-pointer {scope === 'all'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            All
          </button>
          <button
            type="button"
            onclick={() => (scope = 'mine')}
            class="flex items-center gap-1 px-2 py-1 rounded transition-colors cursor-pointer {scope === 'mine'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <User class="w-3 h-3" />
            <span>Personal</span>
          </button>
          <button
            type="button"
            onclick={() => (scope = 'team')}
            class="flex items-center gap-1 px-2 py-1 rounded transition-colors cursor-pointer {scope === 'team'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Users class="w-3 h-3" />
            <span>Team</span>
          </button>
          <button
            type="button"
            onclick={() => (scope = 'org')}
            class="flex items-center gap-1 px-2 py-1 rounded transition-colors cursor-pointer {scope === 'org'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Building2 class="w-3 h-3" />
            <span>Org</span>
          </button>
        </div>

        <!-- Collection Filter -->
        <select
          bind:value={selectedCollectionId}
          class="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 py-1 px-2 rounded-md text-[11px] border border-neutral-200 dark:border-neutral-700 focus:outline-hidden cursor-pointer max-w-40 truncate"
        >
          <option value="all">All Collections</option>
          {#each collections as c (c.id)}
            <option value={c.id}>
              {c.name}
            </option>
          {/each}
        </select>
      </div>
    </div>
  </div>

  <!-- Main Body: Split-Pane Master-Detail Inspector -->
  <div class="flex-1 flex overflow-hidden">
    <!-- LEFT PANE: Minimalist Chunk Feed (45% on desktop) -->
    <div class="w-full lg:w-[460px] xl:w-[500px] border-r border-neutral-200 dark:border-neutral-800 flex flex-col shrink-0 bg-white dark:bg-neutral-900">
      <!-- Section Header -->
      <div class="px-4 py-2.5 border-b border-neutral-200/80 dark:border-neutral-800 bg-neutral-50/70 dark:bg-neutral-900 flex items-center justify-between text-xs shrink-0">
        <div class="flex items-center gap-1.5">
          <span class="font-semibold text-neutral-700 dark:text-neutral-300">
            Ranked Results ({results.length})
          </span>
          <span class="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">
            · top {resultLimit}
          </span>
        </div>
        <span class="text-[11px] text-neutral-400 dark:text-neutral-500">
          Click passage to inspect
        </span>
      </div>

      <!-- Scrollable Passages List -->
      <div class="flex-1 overflow-y-auto divide-y divide-neutral-100 dark:divide-neutral-800/80">
        {#if results.length === 0}
          <div class="h-64 flex flex-col items-center justify-center text-center p-6">
            <Search class="w-8 h-8 text-neutral-300 dark:text-neutral-600 mb-2" />
            <h3 class="text-sm font-semibold text-neutral-700 dark:text-neutral-300">No matching passages</h3>
            <p class="text-xs text-neutral-400 dark:text-neutral-500 max-w-xs mt-1">
              Try adjusting your query or resetting scope filter to "All".
            </p>
          </div>
        {:else}
          {#each results as item (item.chunk.id)}
            {@const { chunk, document: doc, collection: col, score } = item}
            {@const isSelected = activeResult?.chunk.id === chunk.id}
            {@const matchPercent = Math.round(score * 100)}

            <div
              role="button"
              tabindex="0"
              onclick={() => handleSelectChunk(chunk.id)}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  handleSelectChunk(chunk.id);
                }
              }}
              class="p-4 text-left transition-all cursor-pointer relative {isSelected
                ? 'bg-blue-50/70 dark:bg-blue-950/30 border-l-4 border-l-blue-600 pl-3.5'
                : 'hover:bg-neutral-50 dark:hover:bg-neutral-850/60 border-l-4 border-l-transparent'}"
            >
              <!-- Top Row: Document Title & Relevance Badge -->
              <div class="flex items-center justify-between gap-2 mb-1">
                <div class="flex items-center gap-1.5 min-w-0">
                  <FileText class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 shrink-0" />
                  <span class="text-xs font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                    {doc.title}
                  </span>
                </div>

                <span
                  class="shrink-0 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded {matchPercent >= 85
                    ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'}"
                >
                  {matchPercent}%
                </span>
              </div>

              <!-- Metadata Breadcrumb Strip -->
              <div class="flex items-center gap-1.5 text-[11px] text-neutral-400 dark:text-neutral-500 mb-2 truncate">
                <span class="font-medium text-neutral-600 dark:text-neutral-300">{col.name}</span>
                <span>·</span>
                <span class="font-mono text-neutral-600 dark:text-neutral-400">Page {chunk.pageNumber}</span>
                {#if chunk.sectionHeading}
                  <span>·</span>
                  <span class="truncate text-neutral-500 dark:text-neutral-400">{chunk.sectionHeading}</span>
                {/if}
              </div>

              <!-- Clean Text Snippet -->
              <div class="text-xs text-neutral-700 dark:text-neutral-300 line-clamp-3 leading-relaxed">
                <HighlightedSnippet text={chunk.snippet} {query} />
              </div>

              <!-- Mobile Jump Button (hidden on desktop split view) -->
              <div class="mt-2.5 pt-2 border-t border-neutral-100 dark:border-neutral-800 flex lg:hidden items-center justify-end">
                <button
                  type="button"
                  onclick={(e) => {
                    e.stopPropagation();
                    onOpenCitation(doc, chunk.pageNumber, chunk.id);
                  }}
                  class="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400 cursor-pointer"
                >
                  <span>Open Page {chunk.pageNumber}</span>
                  <ArrowRight class="w-3 h-3" />
                </button>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>

    <!-- RIGHT PANE: Live Context Inspector (55% on desktop) -->
    <div class="hidden lg:flex flex-1 flex-col overflow-y-auto bg-neutral-50 dark:bg-neutral-950 p-6 space-y-6">
      {#if activeResult}
        {@const { chunk, document: doc, collection: col, score } = activeResult}
        {@const matchPercent = Math.round(score * 100)}

        <!-- Top Action Card: Document Title & Instant Launch Button -->
        <div class="p-5 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs space-y-4">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500 mb-1.5">
                <span class="font-medium text-neutral-600 dark:text-neutral-300">{col.name}</span>
                <span>·</span>
                <span class="capitalize px-1.5 py-0.2 rounded bg-neutral-100 dark:bg-neutral-800 text-[10px] font-mono">
                  {col.scope === 'mine' ? 'Personal' : col.scope === 'org' ? 'Enterprise' : 'Team'}
                </span>
                <span>·</span>
                <span>Page {chunk.pageNumber} of {doc.pageCount}</span>
              </div>

              <h2 class="text-base font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                <FileText class="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
                <span>{doc.title}</span>
              </h2>

              {#if chunk.sectionHeading}
                <div class="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                  <Bookmark class="w-3 h-3 text-neutral-400" />
                  <span class="font-medium">{chunk.sectionHeading}</span>
                </div>
              {/if}
            </div>

            <!-- Single Master Action CTA -->
            <button
              type="button"
              onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
              class="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer shrink-0"
              title="Open full PDF viewer focused directly on this citation passage"
            >
              <span>Open in Document Viewer</span>
              <ExternalLink class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Metadata Badges -->
          <div class="pt-3 border-t border-neutral-100 dark:border-neutral-800 flex items-center gap-4 text-xs">
            <div class="flex items-center gap-1.5">
              <span class="text-neutral-400 dark:text-neutral-500 text-[11px]">Relevance:</span>
              <span class="font-mono font-semibold text-emerald-600 dark:text-emerald-400">{matchPercent}%</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="text-neutral-400 dark:text-neutral-500 text-[11px]">Token Window:</span>
              <span class="font-mono text-neutral-700 dark:text-neutral-300">{chunk.tokenCount} tokens</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="text-neutral-400 dark:text-neutral-500 text-[11px]">Chunk ID:</span>
              <span class="font-mono text-[10px] text-neutral-500 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 px-1 py-0.5 rounded">
                {chunk.id}
              </span>
            </div>
          </div>
        </div>

        <!-- Middle Inspector Section: Physical Page Raster + Context Window -->
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <!-- Page 1 Miniature Visual Raster -->
          {#if activePage}
            <div class="xl:col-span-1 p-4 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs flex flex-col items-center justify-between">
              <div class="w-full text-center pb-2 border-b border-neutral-100 dark:border-neutral-800 text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Visual Page Map
              </div>

              <div class="my-3">
                <PdfPageThumbnail
                  page={activePage}
                  pageNumber={chunk.pageNumber}
                  isSelected={true}
                  hasActiveChunk={true}
                  activeChunkId={chunk.id}
                  onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
                />
              </div>

              <div class="text-[10px] text-center text-neutral-400 dark:text-neutral-500">
                Click raster to jump to Page {chunk.pageNumber}
              </div>
            </div>
          {/if}

          <!-- Expanded Immediate Reading Passage -->
          <div class="{activePage ? 'xl:col-span-2' : 'xl:col-span-3'} p-5 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between pb-2 border-b border-neutral-100 dark:border-neutral-800 text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                <span>Extracted Citation Passage</span>
                <span class="text-blue-600 dark:text-blue-400 font-mono text-[10px] lowercase">matched passage</span>
              </div>

              <!-- Full snippet with highlighted query matches -->
              <div class="mt-3 p-4 bg-amber-50/40 dark:bg-amber-950/20 border border-amber-200/70 dark:border-amber-900/40 rounded-lg text-xs md:text-sm text-neutral-800 dark:text-neutral-200 leading-relaxed font-sans select-text">
                <HighlightedSnippet text={chunk.snippet} {query} />
              </div>
            </div>

            <!-- Surrounding Page Preview if available -->
            {#if activePage && activePage.content && activePage.content !== chunk.snippet}
              <div class="pt-3 border-t border-neutral-100 dark:border-neutral-800 space-y-1.5">
                <div class="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                  Full Page Context Snippet
                </div>
                <p class="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-3 leading-relaxed">
                  {activePage.content}
                </p>
              </div>
            {/if}
          </div>
        </div>

        <!-- Semantic Entities & Knowledge Tags -->
        {#if (chunk.entities && chunk.entities.length > 0) || (chunk.keywords && chunk.keywords.length > 0)}
          <div class="p-4 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs space-y-2.5">
            <div class="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
              <Tag class="w-3.5 h-3.5 text-neutral-400" />
              <span>Extracted Entities &amp; Metadata Tags</span>
            </div>

            <div class="flex flex-wrap gap-1.5">
              {#if chunk.entities}
                {#each chunk.entities as entity, idx (idx)}
                  <span class="px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900/60 text-blue-700 dark:text-blue-300 text-[11px] font-medium">
                    {entity}
                  </span>
                {/each}
              {/if}
              {#if chunk.keywords}
                {#each chunk.keywords as kw, idx (idx)}
                  <span class="px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 text-[11px]">
                    #{kw}
                  </span>
                {/each}
              {/if}
            </div>
          </div>
        {/if}
      {:else}
        <!-- Empty Selection Placeholder -->
        <div class="flex-1 flex flex-col items-center justify-center text-center p-12 text-neutral-400 dark:text-neutral-600 border border-dashed border-neutral-300 dark:border-neutral-800 rounded-xl bg-white dark:bg-neutral-900">
          <Layers class="w-10 h-10 mb-2 stroke-1" />
          <h3 class="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Select a passage to inspect</h3>
          <p class="text-xs max-w-sm mt-1">
            Choose any chunk from the ranked list to preview its exact page raster, surrounding context, and semantic metadata.
          </p>
        </div>
      {/if}
    </div>
  </div>
</div>
