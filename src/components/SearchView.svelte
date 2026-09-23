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
    Hash,
    Cpu,
    X,
    Filter,
    Upload,
    Loader2,
    CheckCircle2,
    Paperclip
  } from '@lucide/svelte';
  import { fade, fly } from 'svelte/transition';
  import type { Collection, DocumentItem, DocumentPage } from '../types';
  import { executeChunkSearch } from '../utils/retrieval';
  import { chunkTextIntoPages } from '../utils/chunker';
  import { SAMPLE_SEARCH_QUERIES } from '../data/mockData';
  import HighlightedSnippet from './HighlightedSnippet.svelte';
  import PdfPageThumbnail from './PdfPageThumbnail.svelte';

  interface Props {
    documents: DocumentItem[];
    collections: Collection[];
    onOpenCitation: (doc: DocumentItem, pageNumber: number, chunkId: string) => void;
    onUploadDocument?: (doc: DocumentItem) => boolean | void;
  }

  let { documents, collections, onOpenCitation, onUploadDocument }: Props = $props();

  let query = $state('');
  let hasSearched = $state(false);
  let isSearching = $state(false);
  let searchMode = $state<'hybrid' | 'dense' | 'lexical'>('hybrid');
  let scope = $state<'all' | 'mine' | 'team' | 'org'>('all');
  let selectedTeam = $state<string>('all');
  let selectedCollectionId = $state<string>('all');
  let resultLimit = $state<number>(10);
  let selectedChunkId = $state<string | null>(null);

  // File upload state
  let fileInputRef = $state<HTMLInputElement | null>(null);
  let isUploading = $state(false);
  let uploadMessage = $state<string | null>(null);

  // Extract all distinct team names from collections
  let availableTeams = $derived(
    Array.from(
      new Set(
        collections
          .filter((c) => c.scope === 'team' && c.teamName)
          .map((c) => c.teamName as string)
      )
    ).sort()
  );

  // Filter collections based on selected scope and team
  let filteredCollections = $derived(
    collections.filter((c) => {
      if (scope === 'mine') return c.scope === 'mine';
      if (scope === 'org') return c.scope === 'org';
      if (scope === 'team') {
        if (c.scope !== 'team') return false;
        if (selectedTeam !== 'all') return c.teamName === selectedTeam;
        return true;
      }
      return true;
    })
  );

  // If selected collection is no longer in filteredCollections, reset to 'all'
  $effect(() => {
    if (selectedCollectionId !== 'all') {
      const exists = filteredCollections.some((c) => c.id === selectedCollectionId);
      if (!exists) {
        selectedCollectionId = 'all';
      }
    }
  });

  let searchExecution = $derived(
    hasSearched && query.trim()
      ? executeChunkSearch(
          {
            query,
            scope,
            teamName: scope === 'team' ? selectedTeam : undefined,
            collectionId: selectedCollectionId,
            topK: resultLimit,
            minScoreThreshold: 0.12,
            searchMode,
          },
          documents,
          collections
        )
      : { results: [], totalChunksEvaluated: 0, durationMs: 0 }
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

  async function handleExecuteSearch() {
    if (!query.trim()) return;
    hasSearched = true;
    isSearching = true;
    selectedChunkId = null;

    // Simulate realistic neural retrieval latency (embedding generation + reranking)
    await new Promise((r) => setTimeout(r, 450));
    isSearching = false;
  }

  function handleQuickQuery(sample: string) {
    query = sample;
    handleExecuteSearch();
  }

  function handleClear() {
    query = '';
    hasSearched = false;
    isSearching = false;
    selectedChunkId = null;
  }

  async function handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    isUploading = true;
    uploadMessage = `Reading and extracting "${file.name}"...`;

    try {
      let fileText = '';
      if (file.name.endsWith('.md') || file.name.endsWith('.txt')) {
        fileText = await file.text();
      } else {
        fileText = `# ${file.name.replace(/\.[^/.]+$/, '')}
Enterprise architecture specification and technical implementation details extracted from uploaded ${file.name}.

## 1. System Topology & Security Requirements
All service endpoints must enforce bidirectional authentication with cryptographic identity assertions. Microservices operate within isolated network segments with zero implicit trust.

## 2. Token Boundaries & Data Storage
Token life cycles are strictly bounded to 3600 seconds. Data encryption at rest uses AES-256-GCM with hardware-backed key rotation.`;
      }

      await new Promise((r) => setTimeout(r, 400));
      uploadMessage = `Chunking into token windows and generating embeddings...`;
      await new Promise((r) => setTimeout(r, 400));

      const targetCol =
        (selectedCollectionId !== 'all' ? collections.find((c) => c.id === selectedCollectionId) : null) ||
        filteredCollections[0] ||
        collections[0];

      const fileExt = file.name.split('.').pop()?.toLowerCase();
      const docFileType: 'pdf' | 'docx' | 'md' | 'report' =
        fileExt === 'pdf' ? 'pdf' : fileExt === 'docx' ? 'docx' : fileExt === 'md' ? 'md' : 'report';

      const newDocId = `doc-upload-${Date.now()}`;
      const rawPages = [
        {
          pageNumber: 1,
          header: '1. Executive Overview & Architecture',
          content: fileText.slice(0, 800) || `${file.name} document content`,
        },
        {
          pageNumber: 2,
          header: '2. Technical Specifications & Security Controls',
          content: fileText.length > 800 ? fileText.slice(800, 1600) : 'Additional policy and compliance specifications.',
        },
      ];

      const chunkedPages = chunkTextIntoPages(newDocId, targetCol.id, targetCol.scope, rawPages);
      const totalChunks = chunkedPages.reduce((acc, p) => acc + p.chunks.length, 0);

      const newDoc: DocumentItem = {
        id: newDocId,
        collectionId: targetCol.id,
        title: file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '),
        filename: file.name,
        fileType: docFileType,
        source: 'upload',
        uploadedAt: new Date().toISOString(),
        uploadedBy: 'Elena Rostova',
        sizeBytes: file.size || 145000,
        pageCount: rawPages.length,
        chunkCount: totalChunks,
        summary: `Uploaded document ${file.name} with ${totalChunks} chunks indexed into ${targetCol.name}.`,
        entities: ['Enterprise Architecture', 'Uploaded Spec', targetCol.name],
        crossReferences: [],
        semanticTopics: ['Uploaded Document', 'Ingestion', targetCol.scope],
        pages: chunkedPages,
      };

      if (onUploadDocument) {
        onUploadDocument(newDoc);
      }

      uploadMessage = `✓ Ingested "${file.name}" (${totalChunks} chunks) into ${targetCol.name}!`;

      setTimeout(() => {
        isUploading = false;
        uploadMessage = null;
        query = newDoc.title;
        handleExecuteSearch();
      }, 1000);
    } catch {
      isUploading = false;
      uploadMessage = null;
    } finally {
      input.value = '';
    }
  }
</script>

<!-- Hidden File Input for Document Ingestion -->
<input
  type="file"
  bind:this={fileInputRef}
  onchange={handleFileUpload}
  accept=".pdf,.docx,.md,.txt"
  class="hidden"
  id="search-file-upload-input"
/>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Navigation Header -->
  <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-2.5">
      <div class="p-1.5 rounded-md bg-blue-50 dark:bg-blue-950/70 text-blue-600 dark:text-blue-400">
        <Search class="w-4 h-4" />
      </div>
      <div>
        <h1 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Cognify Semantic Search</h1>
      </div>
    </div>

    <div class="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400 font-mono">
      <span>{documents.length} docs indexed</span>
      {#if hasSearched && !isSearching}
        <span>·</span>
        <span class="text-emerald-600 dark:text-emerald-400 font-medium">
          {results.length} matches ({durationMs}ms)
        </span>
      {/if}
    </div>
  </div>

  {#if !hasSearched}
    <!-- Centered Hero State (Stationary & Centered until Search is executed) -->
    <div
      in:fade={{ duration: 200 }}
      class="flex-1 flex flex-col items-center justify-center p-6 min-h-[calc(100vh-3.5rem)] max-w-4xl mx-auto w-full text-center overflow-y-auto"
    >
      <!-- Title & Branding -->
      <div in:fly={{ y: -12, duration: 300 }} class="flex flex-col items-center mb-6">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900/60 text-blue-600 dark:text-blue-400 text-xs font-medium mb-3 shadow-2xs">
          <Sparkles class="w-3.5 h-3.5 text-blue-500" />
          <span>Enterprise Semantic Retrieval Engine</span>
        </div>
        <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
          Search across enterprise knowledge
        </h2>
        <p class="text-xs md:text-sm text-neutral-500 dark:text-neutral-400 max-w-md mt-1.5 leading-relaxed">
          Ask questions or lookup topics to retrieve precise citations and passages ranked by AI.
        </p>
      </div>

      <!-- Centered Search Card & Accessible Controls -->
      <div in:fly={{ y: 12, duration: 300 }} class="w-full max-w-2xl space-y-4">
        <!-- Main Search Bar with Clear, Upload, and Primary Search Button -->
        <div class="relative group flex items-center bg-white dark:bg-neutral-900 rounded-2xl border-2 border-neutral-200 dark:border-neutral-700 focus-within:border-blue-500 dark:focus-within:border-blue-500 shadow-md focus-within:shadow-lg focus-within:shadow-blue-500/5 transition-all p-1.5 pl-4 gap-2">
          <Search class="w-5 h-5 text-neutral-400 dark:text-neutral-500 shrink-0 pointer-events-none group-focus-within:text-blue-500 transition-colors" />
          <input
            type="text"
            bind:value={query}
            onkeydown={(e) => {
              if (e.key === 'Enter') handleExecuteSearch();
            }}
            placeholder="Search questions, policies, specifications, and architecture decisions..."
            class="flex-1 bg-transparent border-none text-sm md:text-base text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden"
          />

          {#if query}
            <button
              type="button"
              onclick={() => (query = '')}
              class="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 p-1.5 rounded-full cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800"
              title="Clear text"
            >
              <X class="w-4 h-4" />
            </button>
          {/if}

          <!-- Upload / Attach File Button -->
          <button
            type="button"
            onclick={() => fileInputRef?.click()}
            class="p-2 text-neutral-500 hover:text-blue-600 dark:text-neutral-400 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded-xl transition-colors cursor-pointer"
            title="Upload file to index (.pdf, .docx, .md, .txt)"
          >
            <Upload class="w-4 h-4" />
          </button>

          <!-- Primary Search Button -->
          <button
            type="button"
            onclick={handleExecuteSearch}
            disabled={!query.trim() || isSearching}
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-xs md:text-sm font-medium flex items-center gap-1.5 transition-all shadow-xs cursor-pointer shrink-0"
          >
            {#if isSearching}
              <Loader2 class="w-4 h-4 animate-spin" />
              <span>Searching...</span>
            {:else}
              <Search class="w-4 h-4" />
              <span>Search</span>
            {/if}
          </button>
        </div>

        <!-- Ingestion Progress / Notification Banner -->
        {#if isUploading && uploadMessage}
          <div in:fade={{ duration: 150 }} class="p-3 bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 rounded-xl text-xs flex items-center justify-center gap-2 text-blue-700 dark:text-blue-300">
            <Loader2 class="w-4 h-4 animate-spin shrink-0" />
            <span class="font-medium">{uploadMessage}</span>
          </div>
        {/if}

        <!-- Accessible Direct Controls Strip -->
        <div class="p-3.5 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs space-y-3 text-left">
          <div class="grid grid-cols-1 sm:grid-cols-2 {scope === 'team' ? 'lg:grid-cols-5' : 'lg:grid-cols-4'} gap-3 text-xs transition-all">
            <!-- 1. Retrieval Mode -->
            <div>
              <span class="block text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Retrieval Mode
              </span>
              <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 text-[11px]">
                <button
                  type="button"
                  onclick={() => (searchMode = 'hybrid')}
                  class="flex-1 py-1.5 px-1 rounded-md text-center transition-colors cursor-pointer {searchMode === 'hybrid'
                    ? 'bg-white dark:bg-neutral-900 text-blue-600 dark:text-blue-400 font-semibold shadow-2xs'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                  title="Blended BM25 lexical + dense semantic vector ranking"
                >
                  Hybrid
                </button>
                <button
                  type="button"
                  onclick={() => (searchMode = 'dense')}
                  class="flex-1 py-1.5 px-1 rounded-md text-center transition-colors cursor-pointer {searchMode === 'dense'
                    ? 'bg-white dark:bg-neutral-900 text-purple-600 dark:text-purple-400 font-semibold shadow-2xs'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                  title="Dense vector semantic similarity"
                >
                  Dense
                </button>
                <button
                  type="button"
                  onclick={() => (searchMode = 'lexical')}
                  class="flex-1 py-1.5 px-1 rounded-md text-center transition-colors cursor-pointer {searchMode === 'lexical'
                    ? 'bg-white dark:bg-neutral-900 text-amber-600 dark:text-amber-400 font-semibold shadow-2xs'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                  title="BM25 keyword term matching"
                >
                  Lexical
                </button>
              </div>
            </div>

            <!-- 2. Chunks Count Limit -->
            <div>
              <span class="block text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Chunks Limit
              </span>
              <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 text-[11px]">
                {#each [10, 30, 50] as count}
                  <button
                    type="button"
                    onclick={() => (resultLimit = count)}
                    class="flex-1 py-1.5 px-1 rounded-md text-center font-mono transition-colors cursor-pointer {resultLimit === count
                      ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 font-semibold shadow-2xs'
                      : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                    title="Retrieve top {count} chunks"
                  >
                    {count}
                  </button>
                {/each}
              </div>
            </div>

            <!-- 3. Scope Selector (Selectable) -->
            <div>
              <label for="hero-scope-select" class="block text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Scope
              </label>
              <select
                id="hero-scope-select"
                bind:value={scope}
                class="w-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 py-1.5 px-2 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 focus:outline-hidden cursor-pointer"
              >
                <option value="all">All Scopes</option>
                <option value="mine">Personal</option>
                <option value="team">Team Knowledge</option>
                <option value="org">Organization</option>
              </select>
            </div>

            <!-- 4. Team Selector (visible if scope === 'team') -->
            {#if scope === 'team'}
              <div in:fly={{ y: -4, duration: 150 }}>
                <label for="hero-team-select" class="block text-[11px] font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider mb-1.5">
                  Select Team
                </label>
                <select
                  id="hero-team-select"
                  bind:value={selectedTeam}
                  class="w-full bg-blue-50/80 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 font-medium py-1.5 px-2 rounded-lg text-xs border border-blue-300 dark:border-blue-800 focus:outline-hidden cursor-pointer truncate"
                >
                  <option value="all">All Teams ({availableTeams.length})</option>
                  {#each availableTeams as team}
                    <option value={team}>{team}</option>
                  {/each}
                </select>
              </div>
            {/if}

            <!-- Collection Filter -->
            <div>
              <label for="hero-collection-select" class="block text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
                Collection
              </label>
              <select
                id="hero-collection-select"
                bind:value={selectedCollectionId}
                class="w-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 py-1.5 px-2 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 focus:outline-hidden cursor-pointer truncate"
              >
                <option value="all">All Collections ({filteredCollections.length})</option>
                {#each filteredCollections as c (c.id)}
                  <option value={c.id}>{c.name}</option>
                {/each}
              </select>
            </div>
          </div>
        </div>

        <!-- Quick Query Suggestion Pills & Upload Action Prompt -->
        <div class="pt-2 text-center space-y-3">
          <div class="flex items-center justify-center gap-2">
            <button
              type="button"
              onclick={() => fileInputRef?.click()}
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-blue-500 dark:hover:border-blue-500 bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-300 text-xs font-medium transition-all shadow-2xs hover:shadow-xs cursor-pointer"
            >
              <Upload class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>Upload Document (.pdf, .docx, .md, .txt)</span>
            </button>
          </div>

          <div class="text-[11px] text-neutral-400 dark:text-neutral-500 flex items-center justify-center gap-1.5">
            <Sparkles class="w-3.5 h-3.5 text-amber-500" />
            <span>Try searching:</span>
          </div>

          <div class="flex flex-wrap items-center justify-center gap-2">
            {#each SAMPLE_SEARCH_QUERIES as sample, idx (idx)}
              <button
                type="button"
                onclick={() => handleQuickQuery(sample)}
                class="px-3 py-1.5 rounded-full bg-white dark:bg-neutral-900 hover:bg-neutral-100 dark:hover:bg-neutral-800 border border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 text-xs transition-all shadow-2xs hover:shadow-xs cursor-pointer"
              >
                {sample}
              </button>
            {/each}
          </div>
        </div>
      </div>
    </div>
  {:else}
    <!-- Active Search Mode: Top Search Bar + Controls Strip -->
    <div
      in:fade={{ duration: 180 }}
      class="px-6 py-3.5 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 shrink-0 space-y-3"
    >
      <!-- Top Row: Input, Clear, Upload, Search Button -->
      <div class="flex items-center gap-3">
        <div class="relative flex-1 max-w-4xl flex items-center bg-neutral-100/80 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 focus-within:border-blue-500 dark:focus-within:border-blue-500 rounded-lg p-1 pl-3 gap-2">
          <Search class="w-4 h-4 text-neutral-400 dark:text-neutral-500 shrink-0 pointer-events-none" />
          <input
            type="text"
            bind:value={query}
            onkeydown={(e) => {
              if (e.key === 'Enter') handleExecuteSearch();
            }}
            placeholder="Search questions, policies, specifications, and architecture decisions..."
            class="flex-1 bg-transparent border-none text-xs md:text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden"
          />

          {#if query}
            <button
              type="button"
              onclick={handleClear}
              class="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 text-xs px-2 py-0.5 rounded cursor-pointer"
            >
              Clear
            </button>
          {/if}

          <!-- Attach / Upload Button in Top Bar -->
          <button
            type="button"
            onclick={() => fileInputRef?.click()}
            class="p-1.5 text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 rounded cursor-pointer transition-colors"
            title="Upload file to index (.pdf, .docx, .md, .txt)"
          >
            <Upload class="w-3.5 h-3.5" />
          </button>

          <!-- Search Button in Top Bar -->
          <button
            type="button"
            onclick={handleExecuteSearch}
            disabled={!query.trim() || isSearching}
            class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-md text-xs font-medium flex items-center gap-1 transition-all cursor-pointer shrink-0"
          >
            {#if isSearching}
              <Loader2 class="w-3.5 h-3.5 animate-spin" />
            {:else}
              <Search class="w-3.5 h-3.5" />
              <span>Search</span>
            {/if}
          </button>
        </div>

        <div class="hidden sm:flex items-center gap-2 text-xs font-mono text-neutral-500 dark:text-neutral-400">
          <span class="px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 uppercase font-semibold text-[10px] {searchMode === 'hybrid' ? 'text-blue-600 dark:text-blue-400' : searchMode === 'dense' ? 'text-purple-600 dark:text-purple-400' : 'text-amber-600 dark:text-amber-400'}">
            {searchMode}
          </span>
          {#if !isSearching}
            <span>{results.length} chunks</span>
          {/if}
        </div>
      </div>

      <!-- Ingestion Notification in Top Bar -->
      {#if isUploading && uploadMessage}
        <div in:fade={{ duration: 150 }} class="p-2 bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 rounded-lg text-xs flex items-center gap-2 text-blue-700 dark:text-blue-300">
          <Loader2 class="w-3.5 h-3.5 animate-spin shrink-0" />
          <span>{uploadMessage}</span>
        </div>
      {/if}

      <!-- Bottom Row: Accessible Filter Strip -->
      <div class="flex items-center justify-between flex-wrap gap-2 text-xs">
        <!-- Quick suggestions scrollable -->
        <div class="flex items-center gap-1.5 overflow-x-auto scrollbar-none py-0.5 max-w-lg">
          <span class="text-[11px] text-neutral-400 dark:text-neutral-500 shrink-0 flex items-center gap-1">
            <Sparkles class="w-3 h-3 text-amber-500" />
            <span>Try:</span>
          </span>
          {#each SAMPLE_SEARCH_QUERIES as sample, idx (idx)}
            <button
              type="button"
              onclick={() => handleQuickQuery(sample)}
              class="px-2.5 py-1 rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-600 dark:text-neutral-300 text-[11px] transition-colors cursor-pointer shrink-0 truncate max-w-xs"
            >
              {sample}
            </button>
          {/each}
        </div>

        <!-- Controls: Retrieval Mode, Chunks Limit, Scope/Org, Collection Filter -->
        <div class="flex items-center gap-2.5 ml-auto flex-wrap">
          <!-- Mode Selector -->
          <div class="flex items-center gap-1 text-[11px]">
            <span class="text-neutral-400 dark:text-neutral-500 font-medium">Mode:</span>
            <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700">
              <button
                type="button"
                onclick={() => {
                  searchMode = 'hybrid';
                  if (hasSearched) handleExecuteSearch();
                }}
                class="px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer {searchMode === 'hybrid'
                  ? 'bg-white dark:bg-neutral-900 text-blue-600 dark:text-blue-400 font-semibold shadow-2xs'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
                title="Blended BM25 + Vector Semantic"
              >
                Hybrid
              </button>
              <button
                type="button"
                onclick={() => {
                  searchMode = 'dense';
                  if (hasSearched) handleExecuteSearch();
                }}
                class="px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer {searchMode === 'dense'
                  ? 'bg-white dark:bg-neutral-900 text-purple-600 dark:text-purple-400 font-semibold shadow-2xs'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
                title="Dense Semantic Vector"
              >
                Dense
              </button>
              <button
                type="button"
                onclick={() => {
                  searchMode = 'lexical';
                  if (hasSearched) handleExecuteSearch();
                }}
                class="px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer {searchMode === 'lexical'
                  ? 'bg-white dark:bg-neutral-900 text-amber-600 dark:text-amber-400 font-semibold shadow-2xs'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900'}"
                title="Lexical BM25 Keywords"
              >
                Lexical
              </button>
            </div>
          </div>

          <!-- Chunks Limit Selector -->
          <div class="flex items-center gap-1 text-[11px]">
            <span class="text-neutral-400 dark:text-neutral-500 font-medium">Chunks:</span>
            <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700">
              {#each [10, 30, 50] as count}
                <button
                  type="button"
                  onclick={() => {
                    resultLimit = count;
                    if (hasSearched) handleExecuteSearch();
                  }}
                  class="px-2 py-0.5 rounded text-[11px] font-mono transition-colors cursor-pointer {resultLimit === count
                    ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 font-semibold shadow-2xs'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
                  title="Retrieve top {count} chunks"
                >
                  {count}
                </button>
              {/each}
            </div>
          </div>

          <!-- Scope / Organization Filter (Selectable) -->
          <div class="flex items-center gap-1 text-[11px]">
            <label for="top-scope-select" class="text-neutral-400 dark:text-neutral-500 font-medium">Scope:</label>
            <select
              id="top-scope-select"
              bind:value={scope}
              onchange={() => {
                if (hasSearched) handleExecuteSearch();
              }}
              class="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 py-1 px-2 rounded-md text-[11px] border border-neutral-200 dark:border-neutral-700 focus:outline-hidden cursor-pointer"
            >
              <option value="all">All Scopes</option>
              <option value="mine">Personal</option>
              <option value="team">Team</option>
              <option value="org">Organization</option>
            </select>
          </div>

          <!-- Team Selector (appears when scope === 'team') -->
          {#if scope === 'team'}
            <div in:fly={{ x: -4, duration: 150 }} class="flex items-center gap-1 text-[11px]">
              <label for="top-team-select" class="text-blue-600 dark:text-blue-400 font-medium">Team:</label>
              <select
                id="top-team-select"
                bind:value={selectedTeam}
                onchange={() => {
                  if (hasSearched) handleExecuteSearch();
                }}
                class="bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-medium py-1 px-2 rounded-md text-[11px] border border-blue-200 dark:border-blue-900/60 focus:outline-hidden cursor-pointer max-w-44 truncate"
              >
                <option value="all">All Teams ({availableTeams.length})</option>
                {#each availableTeams as team}
                  <option value={team}>{team}</option>
                {/each}
              </select>
            </div>
          {/if}

          <!-- Collection Filter -->
          <div class="flex items-center gap-1 text-[11px]">
            <label for="top-collection-select" class="text-neutral-400 dark:text-neutral-500 font-medium">Collection:</label>
            <select
              id="top-collection-select"
              bind:value={selectedCollectionId}
              onchange={() => {
                if (hasSearched) handleExecuteSearch();
              }}
              class="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 py-1 px-2 rounded-md text-[11px] border border-neutral-200 dark:border-neutral-700 focus:outline-hidden cursor-pointer max-w-36 truncate"
            >
              <option value="all">All Collections ({filteredCollections.length})</option>
              {#each filteredCollections as c (c.id)}
                <option value={c.id}>{c.name}</option>
              {/each}
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Body: Results or Simulated Loading State -->
    {#if isSearching}
      <!-- Simulated Neural Retrieval Loading Experience -->
      <div in:fade={{ duration: 150 }} class="flex-1 flex flex-col items-center justify-center p-12 bg-neutral-50 dark:bg-neutral-950 space-y-6">
        <div class="relative flex items-center justify-center">
          <div class="w-14 h-14 rounded-full border-2 border-blue-500/20 border-t-blue-600 animate-spin"></div>
          <Sparkles class="w-6 h-6 text-blue-600 dark:text-blue-400 absolute" />
        </div>
        <div class="text-center space-y-1.5">
          <h3 class="text-sm md:text-base font-semibold text-neutral-800 dark:text-neutral-200 flex items-center justify-center gap-2">
            <span>Executing {searchMode.toUpperCase()} Neural Retrieval</span>
            <span class="inline-block w-2 h-2 rounded-full bg-blue-600 animate-ping"></span>
          </h3>
          <p class="text-xs text-neutral-400 dark:text-neutral-500 font-mono">
            Embedding query, scoring candidate chunks, and cross-ranking citations...
          </p>
        </div>

        <!-- Shimmer Skeleton Placeholders -->
        <div class="w-full max-w-2xl space-y-3.5 animate-pulse mt-2">
          <div class="h-20 bg-neutral-200/70 dark:bg-neutral-850 rounded-xl border border-neutral-200/50 dark:border-neutral-800"></div>
          <div class="h-20 bg-neutral-200/70 dark:bg-neutral-850 rounded-xl border border-neutral-200/50 dark:border-neutral-800"></div>
          <div class="h-20 bg-neutral-200/70 dark:bg-neutral-850 rounded-xl border border-neutral-200/50 dark:border-neutral-800"></div>
        </div>
      </div>
    {:else}
      <!-- Split-Pane Master-Detail Inspector -->
      <div in:fade={{ duration: 200 }} class="flex-1 flex overflow-hidden">
        <!-- LEFT PANE: Minimalist Chunk Feed (45% on desktop) -->
        <div class="w-full lg:w-[460px] xl:w-[500px] border-r border-neutral-200 dark:border-neutral-800 flex flex-col shrink-0 bg-white dark:bg-neutral-900">
          <!-- Section Header -->
          <div class="px-4 py-2.5 border-b border-neutral-200/80 dark:border-neutral-800 bg-neutral-50/70 dark:bg-neutral-900 flex items-center justify-between text-xs shrink-0">
            <div class="flex items-center gap-1.5">
              <span class="font-semibold text-neutral-700 dark:text-neutral-300">
                Ranked Results ({results.length})
              </span>
              <span class="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">
                · top {resultLimit} · {searchMode}
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
                    : 'hover:bg-neutral-50 dark:hover:bg-neutral-800/60 border-l-4 border-l-transparent'}"
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
                    {#if col.scope === 'team' && col.teamName}
                      <span>·</span>
                      <span class="text-blue-600 dark:text-blue-400 font-medium">{col.teamName}</span>
                    {/if}
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
                      class="flex items-center gap-1 text-[11px] text-blue-600 dark:text-blue-400 font-medium hover:underline cursor-pointer"
                    >
                      <span>View in document (Page {chunk.pageNumber})</span>
                      <ArrowRight class="w-3 h-3" />
                    </button>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <!-- RIGHT PANE: Deep Passage Inspection & Document Page View -->
        <div class="flex-1 overflow-y-auto p-6 space-y-6 hidden lg:block bg-neutral-50 dark:bg-neutral-950">
          {#if activeResult}
            {@const { chunk, document: doc, collection: col, score } = activeResult}
            {@const matchPercent = Math.round(score * 100)}

            <!-- Header Card -->
            <div class="p-5 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs space-y-4">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <div class="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/60">
                      {col.name}
                    </span>
                    {#if col.scope === 'team' && col.teamName}
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-900/60">
                        Team: {col.teamName}
                      </span>
                    {/if}
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700">
                      Page {chunk.pageNumber}
                    </span>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider {searchMode === 'hybrid' ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/60' : searchMode === 'dense' ? 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-900/60' : 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-900/60'}">
                      {searchMode} mode
                    </span>
                  </div>
                  <h2 class="text-base font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                    <FileText class="w-4 h-4 text-blue-600 shrink-0" />
                    <span>{doc.title}</span>
                  </h2>
                  {#if chunk.sectionHeading}
                    <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                      Section: <span class="font-medium text-neutral-700 dark:text-neutral-300">{chunk.sectionHeading}</span>
                    </p>
                  {/if}
                </div>

                <!-- Direct Document Jump Button -->
                <button
                  type="button"
                  onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
                  class="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium transition-all shadow-xs cursor-pointer hover:shadow-sm"
                >
                  <span>Jump to Page {chunk.pageNumber}</span>
                  <ExternalLink class="w-3.5 h-3.5" />
                </button>
              </div>

              <!-- Relevance & Scores Breakdown -->
              <div class="pt-3 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between text-xs">
                <div class="flex items-center gap-4">
                  <div>
                    <span class="text-neutral-400 dark:text-neutral-500 text-[11px] block">Total Match</span>
                    <span class="font-mono font-bold text-neutral-900 dark:text-neutral-100 text-sm">
                      {matchPercent}%
                    </span>
                  </div>
                  <div class="h-6 w-px bg-neutral-200 dark:bg-neutral-800"></div>
                  <div>
                    <span class="text-neutral-400 dark:text-neutral-500 text-[11px] block">BM25 Lexical</span>
                    <span class="font-mono text-neutral-700 dark:text-neutral-300 text-xs">
                      {Math.round(activeResult.bm25Score * 100)}%
                    </span>
                  </div>
                  <div>
                    <span class="text-neutral-400 dark:text-neutral-500 text-[11px] block">Vector Semantic</span>
                    <span class="font-mono text-neutral-700 dark:text-neutral-300 text-xs">
                      {Math.round(activeResult.semanticScore * 100)}%
                    </span>
                  </div>
                </div>

                <div class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono">
                  Chunk #{chunk.chunkIndex + 1} ({chunk.tokenCount} tokens)
                </div>
              </div>
            </div>

            <!-- Page Visual Raster & Extracted Passage Cards -->
            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <!-- Exact PDF Page Raster Thumbnail (1 col) -->
              {#if activePage}
                <div class="xl:col-span-1 p-4 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-2xs space-y-3">
                  <div class="flex items-center justify-between pb-2 border-b border-neutral-100 dark:border-neutral-800 text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                    <span>Document Page Raster</span>
                    <span class="text-neutral-400 font-mono text-[10px]">p.{chunk.pageNumber}</span>
                  </div>

                  <div class="w-full aspect-3/4 rounded-lg shadow-2xs overflow-hidden relative group">
                    <PdfPageThumbnail
                      page={activePage}
                      pageNumber={chunk.pageNumber}
                      isSelected={true}
                      hasActiveChunk={true}
                      activeChunkId={chunk.id}
                      onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
                    />
                    <div
                      role="button"
                      tabindex="0"
                      onclick={() => onOpenCitation(doc, chunk.pageNumber, chunk.id)}
                      onkeydown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          onOpenCitation(doc, chunk.pageNumber, chunk.id);
                        }
                      }}
                      class="absolute inset-0 bg-blue-600/10 opacity-0 group-hover:opacity-100 rounded-lg transition-opacity flex items-center justify-center cursor-pointer"
                    >
                      <span class="bg-white/90 dark:bg-neutral-900/90 text-neutral-900 dark:text-neutral-100 text-[11px] font-medium px-2.5 py-1 rounded shadow-xs">
                        Open Full Page
                      </span>
                    </div>
                  </div>

                  <div class="text-[11px] text-neutral-400 dark:text-neutral-500 text-center">
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
    {/if}
  {/if}
</div>
