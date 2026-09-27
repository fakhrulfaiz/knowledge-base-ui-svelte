<script lang="ts">
  import { FileText, Trash2 } from '@lucide/svelte';
  import type { Collection, UserProfile } from '../types';
  import { canDeleteCollection } from '../utils/governance';

  interface Props {
    collection: Collection;
    currentUser?: UserProfile;
    onselect: () => void;
    onDelete?: (col: Collection) => void;
  }

  let { collection, currentUser, onselect, onDelete }: Props = $props();

  let canDelete = $derived(canDeleteCollection(currentUser, collection));

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
    <!-- Scope and Owner + Quick Delete Button -->
    <div class="flex items-center justify-between gap-1.5 text-[11px] text-neutral-400 dark:text-neutral-500 mb-2">
      <div class="flex items-center gap-1.5 truncate">
        <span class="font-medium text-neutral-600 dark:text-neutral-300">{scopeLabel}</span>
        <span aria-hidden="true">·</span>
        <span class="truncate">{collection.createdBy.name}</span>
      </div>

      {#if canDelete && onDelete}
        <button
          type="button"
          onclick={(e) => {
            e.stopPropagation();
            onDelete(collection);
          }}
          class="opacity-0 group-hover:opacity-100 p-1 hover:bg-rose-50 dark:hover:bg-rose-950/60 text-neutral-400 hover:text-rose-600 dark:hover:text-rose-400 rounded transition-all cursor-pointer"
          title="Delete collection"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      {/if}
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
