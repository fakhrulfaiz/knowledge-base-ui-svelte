<script lang="ts">
  import {
    Trash2,
    AlertTriangle,
    Database,
    FolderMinus,
    CheckCircle2,
    X,
    Loader2,
    ShieldAlert,
    FolderKanban
  } from '@lucide/svelte';
  import type { Collection } from '../types';

  interface Props {
    collection: Collection;
    documentCount: number;
    totalChunks: number;
    onClose: () => void;
    onConfirmDelete: (purgeVectors: boolean) => Promise<void> | void;
  }

  let {
    collection,
    documentCount,
    totalChunks,
    onClose,
    onConfirmDelete
  }: Props = $props();

  let isDeleting = $state(false);
  let selectedPurgeOption = $state<boolean>(false); // default safe: preserve in global corpus
  let confirmInput = $state('');
  let requiresTypedConfirmation = $derived(documentCount > 0);
  let canSubmit = $derived(!requiresTypedConfirmation || confirmInput.trim().toLowerCase() === collection.name.trim().toLowerCase());

  async function handleConfirm() {
    if (isDeleting || !canSubmit) return;
    isDeleting = true;
    try {
      await onConfirmDelete(selectedPurgeOption);
    } finally {
      isDeleting = false;
    }
  }
</script>

<div
  class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none"
  role="dialog"
  aria-modal="true"
  aria-labelledby="delete-col-title"
>
  <div class="w-full max-w-lg bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Modal Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400">
          <Trash2 class="w-4 h-4" />
        </div>
        <div>
          <h2 id="delete-col-title" class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Delete Collection
          </h2>
          <p class="text-[11px] text-neutral-500 dark:text-neutral-400 font-mono">
            {collection.id}
          </p>
        </div>
      </div>

      <button
        type="button"
        onclick={onClose}
        disabled={isDeleting}
        class="p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 rounded-md transition-colors cursor-pointer disabled:opacity-50"
        title="Close modal"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Modal Content -->
    <div class="p-6 space-y-4 text-xs">
      <!-- Target Collection Overview Box -->
      <div class="p-3.5 bg-neutral-50 dark:bg-neutral-800/60 rounded-lg border border-neutral-200 dark:border-neutral-700 flex items-start gap-3">
        <div class="p-2 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5">
          <FolderKanban class="w-4 h-4" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-neutral-900 dark:text-neutral-100 truncate text-xs">
            {collection.name}
          </div>
          {#if collection.description}
            <div class="text-[11px] text-neutral-500 dark:text-neutral-400 line-clamp-1 mt-0.5">
              {collection.description}
            </div>
          {/if}
          <div class="flex items-center gap-2 mt-2 text-[10px] font-mono text-neutral-500 dark:text-neutral-400">
            <span class="px-1.5 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 uppercase font-semibold text-neutral-700 dark:text-neutral-300">
              {collection.scope}
            </span>
            <span>{documentCount} document{documentCount === 1 ? '' : 's'}</span>
            <span>·</span>
            <span>{totalChunks} vectors</span>
          </div>
        </div>
      </div>

      <!-- Vector & Document Deletion Options -->
      <div class="space-y-2 pt-1">
        <span class="font-semibold text-neutral-700 dark:text-neutral-300 block">
          Choose Deletion Policy:
        </span>

        <!-- Option 1: Safe Dissociate -->
        <label
          class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors {selectedPurgeOption === false
            ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/20'
            : 'border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/40'}"
        >
          <input
            type="radio"
            name="purgeOption"
            bind:group={selectedPurgeOption}
            value={false}
            class="mt-0.5 text-blue-600 focus:ring-blue-500"
          />
          <div class="flex-1 text-xs">
            <div class="font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-1.5">
              <FolderMinus class="w-3.5 h-3.5 text-blue-500" />
              <span>Delete collection record only (Safe & Recommended)</span>
            </div>
            <p class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1 leading-relaxed">
              Removes this collection from the catalog and reassigns documents to the Global Knowledge Base. Embedded vectors in Milvus remain searchable across enterprise chat and search.
            </p>
          </div>
        </label>

        <!-- Option 2: Full Purge -->
        <label
          class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors {selectedPurgeOption === true
            ? 'border-rose-500 bg-rose-50/50 dark:bg-rose-950/20'
            : 'border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/40'}"
        >
          <input
            type="radio"
            name="purgeOption"
            bind:group={selectedPurgeOption}
            value={true}
            class="mt-0.5 text-rose-600 focus:ring-rose-500"
          />
          <div class="flex-1 text-xs">
            <div class="font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
              <Database class="w-3.5 h-3.5 text-rose-500" />
              <span>Purge collection and delete vectors from Milvus</span>
            </div>
            <p class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1 leading-relaxed">
              Permanently drops any dedicated Milvus vector collections and purges indexing data for documents exclusive to this collection.
            </p>
          </div>
        </label>
      </div>

      <!-- Typed confirmation if documents exist -->
      {#if requiresTypedConfirmation}
        <div class="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-lg space-y-2">
          <div class="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-semibold text-[11px]">
            <AlertTriangle class="w-3.5 h-3.5 shrink-0" />
            <span>Confirm Collection Deletion</span>
          </div>
          <p class="text-[11px] text-neutral-600 dark:text-neutral-300">
            To confirm deletion, please type the collection name <strong class="text-neutral-900 dark:text-neutral-100 font-mono select-all">"{collection.name}"</strong> below:
          </p>
          <input
            type="text"
            bind:value={confirmInput}
            placeholder={collection.name}
            class="w-full px-3 py-1.5 rounded border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 text-xs font-mono outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500"
          />
        </div>
      {/if}
    </div>

    <!-- Modal Footer -->
    <div class="h-14 px-6 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <button
        type="button"
        onclick={onClose}
        disabled={isDeleting}
        class="px-3.5 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 font-medium text-xs transition-colors cursor-pointer disabled:opacity-50"
      >
        Cancel
      </button>

      <button
        type="button"
        onclick={handleConfirm}
        disabled={isDeleting || !canSubmit}
        class="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-xs"
      >
        {#if isDeleting}
          <Loader2 class="w-3.5 h-3.5 animate-spin" />
          <span>Deleting...</span>
        {:else}
          <Trash2 class="w-3.5 h-3.5" />
          <span>Delete Collection</span>
        {/if}
      </button>
    </div>
  </div>
</div>
