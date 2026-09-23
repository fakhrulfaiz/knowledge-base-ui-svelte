<script lang="ts">
  import {
    X,
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut,
    Target,
    Copy,
    Check,
    Info,
    Layers
  } from '@lucide/svelte';
  import type { DocumentItem } from '../types';
  import PdfPageThumbnail from './PdfPageThumbnail.svelte';

  interface Props {
    document: DocumentItem;
    initialPage?: number;
    initialChunkId?: string;
    onClose: () => void;
  }

  let {
    document: doc,
    initialPage = 1,
    initialChunkId,
    onClose,
  }: Props = $props();

  let currentPageNum = $state<number>(1);
  let activeChunkId = $state<string | undefined>(undefined);
  let zoomScale = $state<number>(1);
  let showThumbnails = $state(true);
  let viewMode = $state<'pdf' | 'flow'>('pdf');
  let copied = $state(false);
  let showDetails = $state(false);

  let currentPage = $derived(
    doc.pages.find((p) => p.pageNumber === currentPageNum) || doc.pages[0]
  );

  $effect(() => {
    if (initialPage && initialPage <= doc.pages.length) {
      currentPageNum = initialPage;
    }
    activeChunkId = initialChunkId || undefined;
  });

  $effect(() => {
    const chunkId = activeChunkId;
    const pageNum = currentPageNum;
    if (!chunkId) return;

    const timer = setTimeout(() => {
      const element = window.document.getElementById(`chunk-${chunkId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 150);

    return () => clearTimeout(timer);
  });

  function handlePageChange(pageNum: number) {
    currentPageNum = pageNum;
    if (activeChunkId) {
      const targetPage = doc.pages.find((p) => p.pageNumber === pageNum);
      if (!targetPage?.chunks.some((c) => c.id === activeChunkId)) {
        activeChunkId = undefined;
      }
    }
  }

  function handleCopyCitation() {
    const citationText = `"${doc.title}", Page ${currentPageNum}`;
    navigator.clipboard.writeText(citationText);
    copied = true;
    setTimeout(() => { copied = false; }, 2000);
  }

  function handleZoom(delta: number) {
    zoomScale = Math.min(1.6, Math.max(0.7, +(zoomScale + delta).toFixed(1)));
  }

  function resetZoom() {
    zoomScale = 1;
  }
</script>

<div class="fixed inset-0 z-50 bg-neutral-900/70 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 animate-in fade-in duration-150">
  <div class="w-full max-w-6xl h-[94vh] bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Top Control Bar -->
    <div class="h-14 px-4 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0 select-none">
      <!-- Left: Thumbnail toggle & Title -->
      <div class="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onclick={() => (showThumbnails = !showThumbnails)}
          class="p-1.5 rounded-md text-xs transition-colors cursor-pointer flex items-center gap-1.5 {showThumbnails
            ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 font-medium'
            : 'text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-800 dark:hover:text-neutral-200'}"
          title="Toggle Page Raster Thumbnails"
        >
          <Layers class="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
          <span class="hidden md:inline text-xs">Thumbnails</span>
        </button>

        <div class="h-4 w-px bg-neutral-200 dark:bg-neutral-800"></div>

        <div class="flex items-center gap-2 min-w-0">
          <span class="px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 font-mono text-[10px] uppercase font-semibold shrink-0">
            {doc.fileType}
          </span>
          <h2 class="text-xs sm:text-sm font-semibold text-neutral-900 dark:text-neutral-100 truncate max-w-xs sm:max-w-md">
            {doc.title}
          </h2>
          {#if activeChunkId}
            <span class="hidden lg:inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-[10px] font-semibold">
              <Target class="w-2.5 h-2.5 text-amber-600 dark:text-amber-400" />
              <span>Search Citation</span>
              <button
                type="button"
                onclick={() => (activeChunkId = undefined)}
                class="ml-1 text-amber-700 dark:text-amber-300 hover:text-amber-950 dark:hover:text-white font-bold cursor-pointer"
                title="Dismiss citation highlight"
              >
                ×
              </button>
            </span>
          {/if}
        </div>
      </div>

      <!-- Center: Page Stepper & Zoom Controls -->
      <div class="flex items-center gap-3">
        <!-- Page Stepper -->
        <div class="flex items-center gap-1.5 bg-neutral-100 dark:bg-neutral-800 px-2.5 py-1 rounded-md text-xs border border-neutral-200 dark:border-neutral-700">
          <button
            type="button"
            onclick={() => handlePageChange(Math.max(1, currentPageNum - 1))}
            disabled={currentPageNum <= 1}
            class="p-1 hover:bg-white dark:hover:bg-neutral-700 disabled:opacity-30 disabled:hover:bg-transparent rounded text-neutral-700 dark:text-neutral-300 cursor-pointer"
            title="Previous Page"
          >
            <ChevronLeft class="w-3.5 h-3.5" />
          </button>

          <span class="text-neutral-700 dark:text-neutral-300 text-xs px-1 font-mono tabular-nums">
            Page <strong class="font-semibold text-neutral-900 dark:text-neutral-100">{currentPageNum}</strong> of {doc.pages.length}
          </span>

          <button
            type="button"
            onclick={() => handlePageChange(Math.min(doc.pages.length, currentPageNum + 1))}
            disabled={currentPageNum >= doc.pages.length}
            class="p-1 hover:bg-white dark:hover:bg-neutral-700 disabled:opacity-30 disabled:hover:bg-transparent rounded text-neutral-700 dark:text-neutral-300 cursor-pointer"
            title="Next Page"
          >
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Zoom Controls -->
        <div class="hidden sm:flex items-center gap-1 bg-neutral-100 dark:bg-neutral-800 p-0.5 rounded-md border border-neutral-200 dark:border-neutral-700 text-xs">
          <button
            type="button"
            onclick={() => handleZoom(-0.1)}
            class="p-1 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-white dark:hover:bg-neutral-700 rounded cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut class="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onclick={resetZoom}
            class="px-1.5 py-0.5 text-[11px] font-mono text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 cursor-pointer"
            title="Reset Zoom"
          >
            {Math.round(zoomScale * 100)}%
          </button>

          <button
            type="button"
            onclick={() => handleZoom(0.1)}
            class="p-1 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-white dark:hover:bg-neutral-700 rounded cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- View Mode Toggle: Formatted PDF vs Flow -->
        <div class="hidden md:flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700 text-xs">
          <button
            type="button"
            onclick={() => (viewMode = 'pdf')}
            class="px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer {viewMode === 'pdf'
              ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-2xs'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'}"
          >
            PDF Page
          </button>
          <button
            type="button"
            onclick={() => (viewMode = 'flow')}
            class="px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer {viewMode === 'flow'
              ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-2xs'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'}"
          >
            Clean Flow
          </button>
        </div>
      </div>

      <!-- Right: Actions -->
      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={handleCopyCitation}
          class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors cursor-pointer"
          title="Copy citation reference"
        >
          {#if copied}
            <Check class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          {:else}
            <Copy class="w-3.5 h-3.5" />
          {/if}
          <span>{copied ? 'Copied' : 'Cite'}</span>
        </button>

        <button
          type="button"
          onclick={() => (showDetails = !showDetails)}
          class="p-1.5 rounded-md text-xs transition-colors cursor-pointer {showDetails
            ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
            : 'text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          title="Document details"
        >
          <Info class="w-4 h-4" />
        </button>

        <button
          type="button"
          onclick={onClose}
          class="p-1.5 rounded-md text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors ml-1 cursor-pointer"
        >
          <X class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Main Body Layout -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Left Thumbnail Strip (Rasterized Page Previews) -->
      {#if showThumbnails}
        <aside class="w-36 sm:w-44 bg-neutral-50 dark:bg-neutral-950 border-r border-neutral-200 dark:border-neutral-800 overflow-y-auto p-3 flex flex-col items-center gap-3 shrink-0 select-none">
          <div class="w-full text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 px-1 flex items-center justify-between">
            <span>Pages ({doc.pages.length})</span>
            <span class="text-[9px] font-mono">Raster</span>
          </div>

          {#each doc.pages as p (p.pageNumber)}
            {@const isSelected = p.pageNumber === currentPageNum}
            {@const hasActiveChunk = Boolean(activeChunkId) && p.chunks.some((c) => c.id === activeChunkId)}

            <PdfPageThumbnail
              page={p}
              pageNumber={p.pageNumber}
              {isSelected}
              {hasActiveChunk}
              activeChunkId={activeChunkId}
              onclick={() => handlePageChange(p.pageNumber)}
            />
          {/each}
        </aside>
      {/if}

      <!-- Center Document Reading Canvas -->
      <div
        class="flex-1 overflow-y-auto p-4 sm:p-8 flex justify-center bg-neutral-200/50 dark:bg-neutral-950/70"
      >
        <!-- Rendered PDF Page Simulator -->
        <div
          class="w-full max-w-3xl bg-white dark:bg-neutral-900 shadow-md border border-neutral-300 dark:border-neutral-800 transition-transform duration-150 origin-top text-neutral-900 dark:text-neutral-100 {viewMode === 'pdf' ? 'p-8 sm:p-14 min-h-[900px] flex flex-col justify-between' : 'p-6 sm:p-10 rounded-lg'}"
          style="transform: scale({zoomScale});"
        >
          <!-- Top PDF Running Header -->
          <div>
            {#if viewMode === 'pdf'}
              <div class="border-b-2 border-neutral-900 dark:border-neutral-100 pb-3 mb-8">
                <div class="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-1">
                  <span>CONFIDENTIAL // INTERNAL ARCHITECTURE SPECIFICATION</span>
                  <span class="tabular-nums">ID: {doc.id.toUpperCase()}</span>
                </div>
                <div class="flex items-center justify-between text-xs text-neutral-700 dark:text-neutral-300">
                  <span class="font-semibold">{doc.title}</span>
                  <span class="font-mono text-[11px] tabular-nums">
                    Page {currentPageNum} of {doc.pages.length}
                  </span>
                </div>
              </div>
            {/if}

            <!-- Page Title / Subhead -->
            {#if currentPage?.header}
              <div class="mb-6 pb-2 border-b border-neutral-100 dark:border-neutral-800">
                <h3 class="text-base font-bold text-neutral-900 dark:text-neutral-100 font-sans">
                  {currentPage.header}
                </h3>
              </div>
            {/if}

            <!-- Render Chunks / Paragraphs on this Page -->
            <div class="space-y-6 font-serif">
              {#each currentPage?.chunks || [] as chunk (chunk.id)}
                {@const isHighlighted = Boolean(activeChunkId) && activeChunkId === chunk.id}

                <div
                  id={`chunk-${chunk.id}`}
                  class="relative transition-all duration-300 rounded-md {isHighlighted
                    ? 'border-l-4 border-amber-500 bg-amber-50/80 dark:bg-amber-950/40 p-4 ring-1 ring-amber-300/80 dark:ring-amber-800/80 shadow-xs'
                    : 'p-2'}"
                >
                  <!-- Highlight citation badge -->
                  {#if isHighlighted}
                    <div class="mb-2 flex items-center justify-between border-b border-amber-200/80 dark:border-amber-800/60 pb-1.5 text-xs font-semibold text-amber-900 dark:text-amber-300 font-sans">
                      <span class="flex items-center gap-1.5">
                        <Target class="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                        <span>Referenced Citation Span</span>
                      </span>
                      <span class="text-[10px] text-amber-700 dark:text-amber-400 font-mono">
                        Page {chunk.pageNumber} · Section {chunk.chunkIndex + 1}
                      </span>
                    </div>
                  {/if}

                  <!-- Section Heading -->
                  {#if chunk.sectionHeading}
                    <h4 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-2 font-sans">
                      {chunk.sectionHeading}
                    </h4>
                  {/if}

                  <!-- Text -->
                  <p class="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 whitespace-pre-line">
                    {chunk.snippet}
                  </p>
                </div>
              {/each}
            </div>
          </div>

          <!-- Bottom PDF Running Footer -->
          {#if viewMode === 'pdf'}
            <div class="mt-16 pt-4 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between text-[10px] font-mono text-neutral-400 dark:text-neutral-500 select-none">
              <span>ENTERPRISE SPECIFICATION · {doc.filename}</span>
              <span class="tabular-nums">PAGE {currentPageNum}</span>
            </div>
          {/if}
        </div>
      </div>

      <!-- Right Info Drawer -->
      {#if showDetails}
        <aside class="w-72 bg-white dark:bg-neutral-900 border-l border-neutral-200 dark:border-neutral-800 p-5 overflow-y-auto space-y-4 shrink-0 text-xs text-neutral-600 dark:text-neutral-400 animate-in slide-in-from-right-4 duration-150">
          <div>
            <span class="font-semibold text-neutral-900 dark:text-neutral-100 block mb-1">
              Document Overview
            </span>
            <p class="leading-relaxed text-neutral-600 dark:text-neutral-400">{doc.summary}</p>
          </div>

          <div class="pt-3 border-t border-neutral-100 dark:border-neutral-800 space-y-2">
            <div class="flex justify-between">
              <span class="text-neutral-400 dark:text-neutral-500">File Type:</span>
              <span class="font-mono uppercase text-neutral-800 dark:text-neutral-200 font-semibold">
                {doc.fileType}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-neutral-400 dark:text-neutral-500">Pages:</span>
              <span class="font-mono text-neutral-800 dark:text-neutral-200">{doc.pageCount}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-neutral-400 dark:text-neutral-500">Uploaded by:</span>
              <span class="text-neutral-800 dark:text-neutral-200">{doc.uploadedBy}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-neutral-400 dark:text-neutral-500">Ingestion Date:</span>
              <span class="text-neutral-800 dark:text-neutral-200">
                {new Date(doc.uploadedAt).toLocaleDateString()}
              </span>
            </div>
          </div>

          {#if doc.entities.length > 0}
            <div class="pt-3 border-t border-neutral-100 dark:border-neutral-800">
              <span class="font-semibold text-neutral-900 dark:text-neutral-100 block mb-1.5">
                Topics & Entities
              </span>
              <div class="flex flex-wrap gap-1">
                {#each doc.entities as e, i (i)}
                  <span
                    class="px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 text-[11px]"
                  >
                    {e}
                  </span>
                {/each}
              </div>
            </div>
          {/if}
        </aside>
      {/if}
    </div>
  </div>
</div>
