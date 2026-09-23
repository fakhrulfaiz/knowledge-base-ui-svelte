<script lang="ts">
  import { FileText, FileCode, File } from '@lucide/svelte';
  import type { DocumentItem } from '../types';

  interface Props {
    doc: DocumentItem;
    onclick?: () => void;
  }

  let { doc, onclick }: Props = $props();

  let isPdf = $derived(doc.fileType.toLowerCase() === 'pdf');
  let isMd = $derived(
    doc.fileType.toLowerCase() === 'md' ||
    doc.fileType.toLowerCase() === 'markdown' ||
    doc.fileType.toLowerCase() === 'txt'
  );
</script>

<!-- Google Drive Style Minimalist Document Card -->
<div
  role="button"
  tabindex="0"
  {onclick}
  onkeydown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') onclick?.();
  }}
  class="group bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 hover:border-neutral-400 dark:hover:border-neutral-600 hover:shadow-xs transition-all cursor-pointer flex flex-col overflow-hidden text-left"
  title={doc.title}
>
  <!-- Top Bar: Icon + File Title (Single-line, Google Drive style) -->
  <div class="px-3 py-2.5 flex items-center gap-2 border-b border-neutral-100 dark:border-neutral-800/80 bg-white dark:bg-neutral-900 min-w-0">
    {#if isPdf}
      <div class="p-1 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 shrink-0">
        <FileText class="w-3.5 h-3.5" />
      </div>
    {:else if isMd}
      <div class="p-1 rounded bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 shrink-0">
        <FileCode class="w-3.5 h-3.5" />
      </div>
    {:else}
      <div class="p-1 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shrink-0">
        <File class="w-3.5 h-3.5" />
      </div>
    {/if}

    <span class="text-xs font-medium text-neutral-800 dark:text-neutral-200 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
      {doc.title}
    </span>
  </div>

  <!-- Center Thumbnail: Clean Document Raster Box -->
  <div class="h-36 bg-neutral-50 dark:bg-neutral-950/80 flex items-center justify-center p-3 overflow-hidden select-none">
    {#if isPdf}
      <!-- PDF Document Miniature Raster Sheet -->
      <div class="w-24 h-30 bg-white dark:bg-neutral-850 rounded-xs shadow-xs border border-neutral-200 dark:border-neutral-750 p-2 flex flex-col justify-between group-hover:shadow-sm transition-shadow">
        <div>
          <!-- Miniature Red PDF Header Bar -->
          <div class="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-750 pb-1 mb-1.5">
            <div class="w-8 h-1 bg-rose-500 rounded-2xs"></div>
            <div class="w-3 h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs"></div>
          </div>
          <!-- Heading line -->
          <div class="w-14 h-1.5 bg-neutral-700 dark:bg-neutral-300 rounded-2xs mb-2"></div>
          <!-- Text raster lines -->
          <div class="space-y-1">
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-full"></div>
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-5/6"></div>
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-4/6"></div>
          </div>
          <div class="mt-2 space-y-1">
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-full"></div>
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-3/4"></div>
          </div>
        </div>
        <!-- Bottom raster line -->
        <div class="pt-1 border-t border-neutral-100 dark:border-neutral-800 flex justify-between">
          <div class="w-6 h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs"></div>
          <div class="w-2 h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs"></div>
        </div>
      </div>
    {:else if isMd}
      <!-- Markdown / Text Iron Metallic Sheet -->
      <div class="w-24 h-30 bg-slate-900 dark:bg-zinc-950 rounded-xs shadow-xs border border-slate-700/80 dark:border-zinc-800 p-2 flex flex-col justify-between font-mono text-[7px] group-hover:border-slate-500 transition-colors">
        <div>
          <!-- Iron Header with Markdown Token -->
          <div class="flex items-center gap-1 border-b border-slate-800 dark:border-zinc-800 pb-1 mb-1.5">
            <span class="text-cyan-400 font-bold text-[7px]">#</span>
            <div class="w-10 h-1 bg-cyan-400/80 rounded-2xs"></div>
          </div>
          <!-- Iron Code / Quote Block -->
          <div class="p-1 rounded bg-slate-800/90 dark:bg-zinc-900 border border-slate-700/60 mb-1.5 space-y-1">
            <div class="h-0.5 bg-emerald-400/80 rounded-2xs w-3/4"></div>
            <div class="h-0.5 bg-emerald-400/60 rounded-2xs w-1/2"></div>
          </div>
          <!-- Body lines -->
          <div class="space-y-1">
            <div class="h-0.5 bg-slate-600 dark:bg-zinc-700 rounded-2xs w-full"></div>
            <div class="h-0.5 bg-slate-600 dark:bg-zinc-700 rounded-2xs w-4/5"></div>
            <div class="h-0.5 bg-slate-600 dark:bg-zinc-700 rounded-2xs w-3/5"></div>
          </div>
        </div>
        <!-- Iron Bottom Badge -->
        <div class="pt-1 border-t border-slate-800 dark:border-zinc-800 flex justify-between items-center text-[6px] text-slate-500">
          <span>.MD</span>
          <div class="w-4 h-0.5 bg-slate-700 rounded-2xs"></div>
        </div>
      </div>
    {:else}
      <!-- Generic File Sheet -->
      <div class="w-24 h-30 bg-white dark:bg-neutral-850 rounded-xs shadow-xs border border-neutral-200 dark:border-neutral-750 p-2 flex flex-col justify-between">
        <div>
          <div class="w-8 h-1 bg-blue-500 rounded-2xs mb-2"></div>
          <div class="w-12 h-1.5 bg-neutral-700 dark:bg-neutral-300 rounded-2xs mb-2"></div>
          <div class="space-y-1">
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-full"></div>
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-4/5"></div>
            <div class="h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs w-3/5"></div>
          </div>
        </div>
        <div class="w-6 h-0.5 bg-neutral-300 dark:bg-neutral-600 rounded-2xs"></div>
      </div>
    {/if}
  </div>
</div>
