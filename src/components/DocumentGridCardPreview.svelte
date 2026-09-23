<script lang="ts">
  import { FileText } from '@lucide/svelte';

  interface Props {
    title: string;
    fileType: string;
    pageCount?: number;
    firstPageSnippet: string;
  }

  let {
    title,
    fileType,
    pageCount,
    firstPageSnippet,
  }: Props = $props();
</script>

<!-- Enterprise Minimalist Document Preview Box -->
<div class="w-full bg-neutral-50/70 dark:bg-neutral-850/60 rounded-t-lg border-b border-neutral-200/80 dark:border-neutral-800 p-3.5 select-none group-hover:bg-neutral-100/50 dark:group-hover:bg-neutral-800/80 transition-colors">
  <!-- Inner Document Card Box -->
  <div class="w-full min-h-[110px] bg-white dark:bg-neutral-900 rounded-md border border-neutral-200/90 dark:border-neutral-750 p-3 shadow-2xs flex flex-col justify-between">
    <!-- Header of Document Preview -->
    <div class="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-800 pb-1.5 mb-2">
      <div class="flex items-center gap-1.5">
        <FileText class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
        <span class="text-[11px] font-semibold tracking-wider uppercase text-neutral-700 dark:text-neutral-300">
          {fileType}
        </span>
      </div>
      <span class="text-[10px] font-medium text-neutral-400 dark:text-neutral-500">
        Preview
      </span>
    </div>

    <!-- Text Snippet (High-contrast, readable font for enterprise accessibility) -->
    <p class="text-xs text-neutral-600 dark:text-neutral-300 leading-relaxed line-clamp-3 font-normal">
      {firstPageSnippet}
    </p>

    <!-- Document Excerpt indicator -->
    <div class="pt-1.5 mt-2 border-t border-neutral-100 dark:border-neutral-800/80 flex items-center justify-between text-[10px] text-neutral-400 dark:text-neutral-500">
      <span class="truncate max-w-[170px]">{title}</span>
      <span>Excerpt</span>
    </div>
  </div>
</div>
