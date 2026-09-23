<script lang="ts">
  import {
    Search,
    FileText,
    ArrowRight,
    Bookmark
  } from '@lucide/svelte';
  import type { Collection, DocumentItem } from '../types';
  import { executeChunkSearch } from '../utils/retrieval';
  import { SAMPLE_SEARCH_QUERIES } from '../data/mockData';
  import HighlightedSnippet from './HighlightedSnippet.svelte';

  interface Props {
    documents: DocumentItem[];
    collections: Collection[];
    onOpenCitation: (doc: DocumentItem, pageNumber: number, chunkId: string) => void;
  }

  let { documents, collections, onOpenCitation }: Props = $props();

  let query = $state('Zero Trust mTLS architecture');
  let scope = $state<'all' | 'team' | 'org'>('all');
  let selectedCollectionId = $state<string>('all');
  let resultLimit = $state<number>(5);

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
</script>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Header -->
  <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-2">
      <Search class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
      <h1 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Search Knowledge Base</h1>
    </div>

    <div class="text-xs text-neutral-400 dark:text-neutral-500">
      <span>{documents.length} documents searchable</span>
      {#if results.length > 0}
        <span> · Found {results.length} relevant passages</span>
      {/if}
    </div>
  </div>

  <!-- Clean, Simple Search Area -->
  <div class="px-6 py-5 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 shrink-0 space-y-3">
    <!-- Main Search Bar -->
    <div class="relative max-w-3xl">
      <Search class="w-4 h-4 text-neutral-400 dark:text-neutral-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      <input
        type="text"
        bind:value={query}
        placeholder="Search questions, policies, specifications, and runbooks..."
        class="w-full pl-10 pr-10 py-2.5 bg-neutral-100/80 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-800/90 focus:bg-white dark:focus:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500 transition-all"
      />
      {#if query}
        <button
          type="button"
          onclick={() => (query = '')}
          class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 text-xs px-1.5 py-0.5 rounded cursor-pointer"
        >
          Clear
        </button>
      {/if}
    </div>

    <!-- Quick query suggestions -->
    <div class="flex items-center gap-2 overflow-x-auto text-xs scrollbar-none pt-1">
      <span class="text-[11px] text-neutral-400 dark:text-neutral-500 shrink-0">Suggestions:</span>
      {#each SAMPLE_SEARCH_QUERIES as sample, idx (idx)}
        <button
          type="button"
          onclick={() => (query = sample)}
          class="px-2.5 py-1 rounded bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-600 dark:text-neutral-300 text-xs transition-colors cursor-pointer shrink-0"
        >
          {sample}
        </button>
      {/each}
    </div>

    <!-- Filters Row: Clean and simple -->
    <div class="pt-2 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between flex-wrap gap-3 text-xs">
      <div class="flex items-center gap-4">
        <!-- Scope Filter -->
        <div class="flex items-center gap-1.5">
          <span class="text-neutral-400 dark:text-neutral-500">Scope:</span>
          <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700">
            <button
              type="button"
              onclick={() => (scope = 'all')}
              class="px-2.5 py-1 rounded text-xs transition-colors cursor-pointer {scope === 'all'
                ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-medium'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
            >
              All
            </button>
            <button
              type="button"
              onclick={() => (scope = 'org')}
              class="px-2.5 py-1 rounded text-xs transition-colors cursor-pointer {scope === 'org'
                ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-medium'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
            >
              Organization
            </button>
            <button
              type="button"
              onclick={() => (scope = 'team')}
              class="px-2.5 py-1 rounded text-xs transition-colors cursor-pointer {scope === 'team'
                ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-medium'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
            >
              Team
            </button>
          </div>
        </div>

        <!-- Collection Dropdown -->
        <div class="flex items-center gap-1.5">
          <span class="text-neutral-400 dark:text-neutral-500">Collection:</span>
          <select
            bind:value={selectedCollectionId}
            class="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 py-1 px-2 rounded text-xs border border-neutral-200 dark:border-neutral-700 focus:outline-hidden cursor-pointer max-w-48 truncate"
          >
            <option value="all" class="dark:bg-neutral-800">All Collections</option>
            {#each collections as c (c.id)}
              <option value={c.id} class="dark:bg-neutral-800">
                {c.name}
              </option>
            {/each}
          </select>
        </div>
      </div>

      <div class="text-[11px] text-neutral-400 dark:text-neutral-500">
        Searched in {durationMs}ms
      </div>
    </div>
  </div>

  <!-- Results View -->
  <div class="flex-1 overflow-y-auto p-6 max-w-4xl space-y-4">
    {#if results.length === 0}
      <div class="h-60 border border-dashed border-neutral-300 dark:border-neutral-800 rounded-lg flex flex-col items-center justify-center text-center p-6 bg-white dark:bg-neutral-900">
        <Search class="w-8 h-8 text-neutral-300 dark:text-neutral-600 mb-2" />
        <h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300">No matching passages found</h3>
        <p class="text-xs text-neutral-400 dark:text-neutral-500 max-w-sm mt-1">
          Try a different keyword or set the scope to "All".
        </p>
      </div>
    {:else}
      <div class="space-y-3">
        <div class="text-xs text-neutral-400 dark:text-neutral-500">
          Showing top results for <strong class="text-neutral-700 dark:text-neutral-300">"{query}"</strong>
        </div>

        {#each results as item (item.chunk.id)}
          {@const { chunk, document: doc, collection: col, score } = item}
          {@const matchPercent = Math.round(score * 100)}

          <div class="p-4 bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 hover:shadow-xs transition-all space-y-2.5">
            <!-- Top Bar: Title & View Button -->
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500 mb-1">
                  <span class="font-medium text-neutral-600 dark:text-neutral-300">{col.name}</span>
                  <span>·</span>
                  <span>Page {chunk.pageNumber}</span>
                  <span>·</span>
                  <span class="text-emerald-700 dark:text-emerald-400 font-medium">{matchPercent}% match</span>
                </div>

                <button
                  type="button"
                  onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
                  class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors cursor-pointer flex items-center gap-1.5 text-left"
                >
                  <FileText class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 shrink-0" />
                  <span>{doc.title}</span>
                </button>
              </div>

              <button
                type="button"
                onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
                class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-xs transition-colors cursor-pointer shrink-0"
              >
                <span>Open Page {chunk.pageNumber}</span>
                <ArrowRight class="w-3 h-3" />
              </button>
            </div>

            <!-- Section Title -->
            {#if chunk.sectionHeading}
              <div class="text-xs font-medium text-neutral-700 dark:text-neutral-300 flex items-center gap-1">
                <Bookmark class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
                <span>{chunk.sectionHeading}</span>
              </div>
            {/if}

            <!-- Snippet -->
            <div class="p-3 bg-neutral-50 dark:bg-neutral-800/60 rounded-md border border-neutral-100 dark:border-neutral-800 text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed font-sans">
              <HighlightedSnippet text={chunk.snippet} {query} />
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>
