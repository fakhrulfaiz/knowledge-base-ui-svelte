<script lang="ts">
  import { FileText } from '@lucide/svelte';
  import type { Collection } from '../types';

  interface Props {
    collection: Collection;
    onselect: () => void;
  }

  let { collection, onselect }: Props = $props();

  let formattedDate = $derived(
    new Date(collection.updatedAt).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  );

  let scopeLabel = $derived(
    collection.scope === 'mine'
      ? 'Personal'
      : collection.scope === 'org'
      ? 'Enterprise'
      : collection.teamName || 'Team'
  );
</script>

<div
  role="button"
  tabindex="0"
  onclick={onselect}
  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onselect(); }}
  class="p-4 bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between group"
>
  <div>
    <!-- Scope, Owner, and Quota badge -->
    <div class="flex items-center justify-between text-[11px] text-neutral-400 dark:text-neutral-500 mb-2">
      <div class="flex items-center gap-1.5 truncate">
        <span class="font-medium text-neutral-600 dark:text-neutral-300">{scopeLabel}</span>
        <span aria-hidden="true">·</span>
        <span class="truncate">{collection.createdBy.name}</span>
      </div>

      <span class="shrink-0 px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 text-[10px] font-mono font-semibold border border-blue-100 dark:border-blue-900/60">
        {collection.allocatedGb || 10} GB Quota
      </span>
    </div>

    <!-- Collection Title -->
    <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-1">
      {collection.name}
    </h3>

    <!-- Description -->
    <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5 line-clamp-2 leading-relaxed">
      {collection.description}
    </p>
  </div>

  <!-- Footer Metrics & Metadata -->
  <div class="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
    <div class="flex items-center gap-2 text-[11px] font-mono tabular-nums">
      <span class="flex items-center gap-1 text-neutral-600 dark:text-neutral-300">
        <FileText class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
        {collection.documentCount} docs
      </span>
      <span aria-hidden="true" class="text-neutral-300 dark:text-neutral-700">·</span>
      <span>{collection.totalChunks} chunks</span>
    </div>

    <div class="text-[11px] text-neutral-400 dark:text-neutral-500">
      {formattedDate}
    </div>
  </div>
</div>
