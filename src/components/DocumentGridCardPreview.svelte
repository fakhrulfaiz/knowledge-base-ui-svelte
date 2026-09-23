<script lang="ts">
  interface Props {
    title: string;
    fileType: string;
    pageCount: number;
    firstPageSnippet: string;
  }

  let {
    title,
    fileType,
    pageCount,
    firstPageSnippet,
  }: Props = $props();
</script>

<div class="relative w-full h-36 bg-white dark:bg-neutral-800/80 rounded-t-lg border-b border-neutral-100 dark:border-neutral-700/60 p-3 flex flex-col justify-between overflow-hidden group-hover:bg-neutral-50/50 dark:group-hover:bg-neutral-800 transition-colors">
  <!-- Background document layout watermark -->
  <div class="space-y-1.5 select-none">
    <div class="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-700/60 pb-1.5 mb-1.5">
      <span class="text-[9px] uppercase font-mono font-bold text-neutral-400 dark:text-neutral-500">
        {fileType} · DOCUMENT PREVIEW
      </span>
      <span class="text-[9px] font-mono text-neutral-400 dark:text-neutral-500">
        {pageCount} {pageCount === 1 ? 'page' : 'pages'}
      </span>
    </div>

    <div class="w-3/4 h-2 bg-neutral-700 dark:bg-neutral-300 rounded-xs mb-1"></div>
    <div class="w-1/2 h-1.5 bg-neutral-300 dark:bg-neutral-600 rounded-xs mb-2"></div>

    <!-- Text snippet preview -->
    <p class="text-[10px] text-neutral-500 dark:text-neutral-400 leading-snug line-clamp-3 font-serif italic">
      "{firstPageSnippet}"
    </p>
  </div>

  <!-- Footer bar -->
  <div class="flex items-center justify-between border-t border-neutral-100 dark:border-neutral-700/60 pt-1 text-[9px] text-neutral-400 dark:text-neutral-500 font-mono">
    <span>INTERNAL SPEC</span>
    <span>PAGE 1 OF {pageCount}</span>
  </div>
</div>
