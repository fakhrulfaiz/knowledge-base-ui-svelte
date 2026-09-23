<script lang="ts">
  import type { DocumentPage } from '../types';
  import { Target } from '@lucide/svelte';

  interface Props {
    page: DocumentPage;
    pageNumber: number;
    isSelected: boolean;
    hasActiveChunk?: boolean;
    activeChunkId?: string;
    onclick?: () => void;
  }

  let {
    page,
    pageNumber,
    isSelected,
    hasActiveChunk = false,
    activeChunkId = '',
    onclick,
  }: Props = $props();
</script>

<button
  type="button"
  {onclick}
  class="group w-full flex flex-col items-center gap-1.5 p-2 rounded-lg transition-all text-left cursor-pointer {isSelected
    ? 'bg-neutral-100 dark:bg-neutral-800 ring-2 ring-neutral-900 dark:ring-blue-500'
    : 'hover:bg-neutral-100/70 dark:hover:bg-neutral-800/70'}"
>
  <!-- Miniature A4 Raster Sheet -->
  <div
    class="relative w-28 h-36 bg-white dark:bg-neutral-850 rounded-xs shadow-xs border transition-all overflow-hidden flex flex-col justify-between p-2 select-none {isSelected
      ? 'border-neutral-800 dark:border-blue-500 shadow-sm'
      : 'border-neutral-200 dark:border-neutral-700 group-hover:border-neutral-300 dark:group-hover:border-neutral-600'}"
  >
    <!-- Raster Top Header -->
    <div>
      <div class="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-750 pb-1 mb-1.5">
        <div class="w-10 h-1 bg-neutral-400 dark:bg-neutral-500 rounded-2xs"></div>
        <div class="text-[7px] font-mono text-neutral-300 dark:text-neutral-500">p.{pageNumber}</div>
      </div>

      <!-- Simulated page heading -->
      <div class="w-16 h-1.5 bg-neutral-700 dark:bg-neutral-300 rounded-2xs mb-2"></div>

      <!-- Simulated content blocks & raster chunks -->
      <div class="space-y-1.5">
        {#each page.chunks as chunk (chunk.id)}
          {@const isTarget = Boolean(activeChunkId) && chunk.id === activeChunkId}
          <div
            class="rounded-2xs p-1 transition-all {isTarget
              ? 'bg-amber-100 dark:bg-amber-950/60 border border-amber-400 dark:border-amber-600 ring-1 ring-amber-300 dark:ring-amber-700'
              : 'bg-neutral-50/50 dark:bg-neutral-800/50'}"
          >
            {#if isTarget}
              <div class="flex items-center gap-0.5 mb-0.5">
                <div class="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
                <div class="w-8 h-1 bg-amber-600 dark:bg-amber-400 rounded-2xs"></div>
              </div>
            {/if}
            <!-- Miniature text lines -->
            <div class="space-y-0.5">
              <div
                class="h-0.5 rounded-2xs w-full {isTarget
                  ? 'bg-amber-700/60 dark:bg-amber-300/60'
                  : 'bg-neutral-300 dark:bg-neutral-600'}"
              ></div>
              <div
                class="h-0.5 rounded-2xs w-4/5 {isTarget
                  ? 'bg-amber-700/60 dark:bg-amber-300/60'
                  : 'bg-neutral-300 dark:bg-neutral-600'}"
              ></div>
              <div
                class="h-0.5 rounded-2xs w-3/4 {isTarget
                  ? 'bg-amber-700/60 dark:bg-amber-300/60'
                  : 'bg-neutral-200 dark:bg-neutral-700'}"
              ></div>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Raster Footer -->
    <div class="border-t border-neutral-100 dark:border-neutral-750 pt-1 flex items-center justify-between">
      <div class="w-6 h-0.5 bg-neutral-200 dark:bg-neutral-600 rounded-2xs"></div>
      <div class="w-3 h-0.5 bg-neutral-300 dark:bg-neutral-500 rounded-2xs"></div>
    </div>

    <!-- Highlight badge on thumbnail - only when active search citation -->
    {#if Boolean(activeChunkId) && hasActiveChunk}
      <div class="absolute top-1 right-1 px-1 py-0.5 bg-amber-500 text-white rounded-xs text-[7px] font-bold shadow-xs flex items-center gap-0.5">
        <Target class="w-2 h-2" />
        <span>CITATION</span>
      </div>
    {/if}
  </div>

  <!-- Page Label -->
  <span
    class="text-[11px] font-mono tabular-nums {isSelected
      ? 'font-semibold text-neutral-900 dark:text-neutral-100'
      : 'text-neutral-500 dark:text-neutral-400'}"
  >
    Page {pageNumber}
  </span>
</button>
