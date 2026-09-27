<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Trash2,
    AlertTriangle,
    Database,
    FolderMinus,
    Layers,
    FileText,
    CheckCircle2,
    X,
    Loader2,
    ShieldAlert
  } from '@lucide/svelte';
  import type { DocumentItem, Collection } from '../types';

  interface OtherReference {
    docId: string;
    collectionId: string;
    collectionName: string;
    scope: string;
    visibility: string;
  }

  interface Props {
    document: DocumentItem;
    collection?: Collection;
    onClose: () => void;
    onConfirmDelete: (purgeVectors: boolean) => Promise<void> | void;
  }

  let { document: doc, collection, onClose, onConfirmDelete }: Props = $props();

  let loadingReferences = $state(true);
  let hasOtherReferences = $state(false);
  let otherReferences = $state<OtherReference[]>([]);
  let isDeleting = $state(false);
  let selectedPurgeOption = $state<boolean>(false); // default to false (safe)

  onMount(async () => {
    try {
      const res = await fetch(`http://localhost:8080/api/documents/${doc.id}/references`);
      if (res.ok) {
        const data = await res.json();
        hasOtherReferences = data.hasOtherReferences ?? false;
        otherReferences = data.otherReferences ?? [];
      } else {
        // Fallback: check if local document list has other entries with same filename
        hasOtherReferences = false;
      }
    } catch (err) {
      console.warn('Failed to fetch document references:', err);
      hasOtherReferences = false;
    } finally {
      loadingReferences = false;
    }
  });

  async function handleConfirm(purgeVectors: boolean) {
    if (isDeleting) return;
    isDeleting = true;
    try {
      await onConfirmDelete(purgeVectors);
    } finally {
      isDeleting = false;
    }
  }
</script>

<div
  class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none"
  role="dialog"
  aria-modal="true"
  aria-labelledby="delete-doc-title"
>
  <div class="w-full max-w-lg bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Modal Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-lg {hasOtherReferences ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400' : 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400'}">
          {#if hasOtherReferences}
            <FolderMinus class="w-4 h-4" />
          {:else}
            <Trash2 class="w-4 h-4" />
          {/if}
        </div>
        <div>
          <h2 id="delete-doc-title" class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {hasOtherReferences ? 'Remove Document from Collection' : 'Delete Document'}
          </h2>
          <p class="text-[11px] text-neutral-500 dark:text-neutral-400 font-mono">
            ID: {doc.id}
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
      <!-- Target Document Overview Box -->
      <div class="p-3 bg-neutral-50 dark:bg-neutral-800/60 rounded-lg border border-neutral-200 dark:border-neutral-700 flex items-start gap-3">
        <div class="p-2 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5">
          <FileText class="w-4 h-4" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-neutral-900 dark:text-neutral-100 truncate text-xs">
            {doc.title}
          </div>
          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
            {doc.filename}
          </div>
          <div class="flex flex-wrap items-center gap-2 mt-2">
            <span class="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-medium text-[10px] flex items-center gap-1">
              <Layers class="w-3 h-3" />
              {collection?.name || 'Current Collection'}
            </span>
            <span class="px-2 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-mono text-[10px]">
              {doc.chunkCount} Chunks / Vectors
            </span>
            <span class="px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700/60 text-neutral-600 dark:text-neutral-300 text-[10px] uppercase font-semibold">
              {doc.visibility || 'shared'}
            </span>
          </div>
        </div>
      </div>

      {#if loadingReferences}
        <div class="p-6 flex flex-col items-center justify-center gap-2 text-neutral-400">
          <Loader2 class="w-5 h-5 animate-spin text-blue-500" />
          <span class="text-xs">Checking collection references across workspace...</span>
        </div>
      {:else if hasOtherReferences}
        <!-- CASE 1: Document is present in OTHER collections -->
        <!-- Requirement: "mke sure if delete document, it should only on collection ya" -->
        <div class="p-3.5 bg-blue-50/80 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/60 rounded-xl space-y-2.5">
          <div class="flex items-center gap-2 text-blue-700 dark:text-blue-400 font-semibold text-xs">
            <CheckCircle2 class="w-4 h-4 shrink-0" />
            <span>Document referenced by {otherReferences.length} other collection{otherReferences.length > 1 ? 's' : ''}</span>
          </div>
          <p class="text-neutral-600 dark:text-neutral-300 text-[11px] leading-relaxed">
            Deleting this document will <strong>only remove it from {collection?.name || 'this collection'}</strong>.
            The physical file and its indexed vector embeddings in Milvus will remain preserved so other collections can continue using them without re-indexing.
          </p>

          <div class="pt-1 border-t border-blue-100 dark:border-blue-900/40">
            <div class="text-[10px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">
              Still Accessible In:
            </div>
            <div class="flex flex-wrap gap-1.5">
              {#each otherReferences as ref}
                <span class="px-2 py-1 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 text-[11px] flex items-center gap-1.5 font-medium">
                  <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                  {ref.collectionName}
                  <span class="text-[9px] text-neutral-400 dark:text-neutral-500 uppercase font-mono">({ref.scope})</span>
                </span>
              {/each}
            </div>
          </div>
        </div>

        <p class="text-neutral-500 dark:text-neutral-400 text-[11px]">
          Click below to confirm removal from <strong>{collection?.name || 'this collection'}</strong>.
        </p>

      {:else}
        <!-- CASE 2: Sole reference (NO other collection contains this document) -->
        <!-- Requirement: "only if no other collection then have warning , you want to delete in vector database too?" -->
        <div class="p-3.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-xl space-y-2">
          <div class="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-semibold text-xs">
            <AlertTriangle class="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>Sole Collection Reference Warning</span>
          </div>
          <p class="text-amber-900 dark:text-amber-200 text-xs font-medium">
            This document is <strong>not referenced by any other collection</strong>.
          </p>
          <div class="text-neutral-700 dark:text-neutral-300 text-xs font-semibold pt-1 flex items-center gap-1.5">
            <Database class="w-4 h-4 text-rose-500" />
            <span>Do you want to delete in vector database too?</span>
          </div>
        </div>

        <!-- Options for Sole Collection Reference -->
        <div class="grid grid-cols-1 gap-2 pt-1">
          <!-- Option A: Remove from collection only (keep vectors) -->
          <button
            type="button"
            onclick={() => (selectedPurgeOption = false)}
            class="p-3 rounded-lg border text-left transition-all cursor-pointer flex items-start gap-3 {!selectedPurgeOption
              ? 'bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 ring-1 ring-blue-500'
              : 'bg-neutral-50 dark:bg-neutral-800/60 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
          >
            <div class="mt-0.5">
              <input
                type="radio"
                name="purgeOption"
                checked={!selectedPurgeOption}
                class="text-blue-600 focus:ring-blue-500"
              />
            </div>
            <div class="flex-1">
              <div class="font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-1.5">
                <span>Remove from Collection Only</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-medium">Safe</span>
              </div>
              <p class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5">
                Removes ownership from {collection?.name || 'this collection'}. Keeps indexed vectors in Milvus so you can re-add it instantly from Drive later without re-indexing.
              </p>
            </div>
          </button>

          <!-- Option B: Delete from collection AND purge vectors -->
          <button
            type="button"
            onclick={() => (selectedPurgeOption = true)}
            class="p-3 rounded-lg border text-left transition-all cursor-pointer flex items-start gap-3 {selectedPurgeOption
              ? 'bg-rose-50/70 dark:bg-rose-950/40 border-rose-500 ring-1 ring-rose-500'
              : 'bg-neutral-50 dark:bg-neutral-800/60 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
          >
            <div class="mt-0.5">
              <input
                type="radio"
                name="purgeOption"
                checked={selectedPurgeOption}
                class="text-rose-600 focus:ring-rose-500"
              />
            </div>
            <div class="flex-1">
              <div class="font-semibold text-rose-700 dark:text-rose-400 flex items-center gap-1.5">
                <span>Delete & Purge in Vector Database Too</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 font-medium">Permanent</span>
              </div>
              <p class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5">
                Removes document and permanently deletes all {doc.chunkCount} vector embeddings and citation telemetry from Milvus standalone.
              </p>
            </div>
          </button>
        </div>
      {/if}
    </div>

    <!-- Modal Footer Actions -->
    <div class="h-16 px-6 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <button
        type="button"
        onclick={onClose}
        disabled={isDeleting}
        class="px-4 py-2 rounded-lg text-xs font-medium text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-800 transition-colors cursor-pointer disabled:opacity-50"
      >
        Cancel
      </button>

      {#if hasOtherReferences}
        <!-- Sole action when other collections reference this file: Remove from collection only -->
        <button
          type="button"
          onclick={() => handleConfirm(false)}
          disabled={isDeleting || loadingReferences}
          class="px-4 py-2 rounded-lg text-xs font-medium bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
        >
          {#if isDeleting}
            <Loader2 class="w-3.5 h-3.5 animate-spin" />
            <span>Removing...</span>
          {:else}
            <FolderMinus class="w-3.5 h-3.5" />
            <span>Remove from Collection</span>
          {/if}
        </button>
      {:else}
        <!-- Two options or dynamic submit button based on selectedPurgeOption -->
        <div class="flex items-center gap-2">
          {#if selectedPurgeOption}
            <button
              type="button"
              onclick={() => handleConfirm(true)}
              disabled={isDeleting || loadingReferences}
              class="px-4 py-2 rounded-lg text-xs font-medium bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
            >
              {#if isDeleting}
                <Loader2 class="w-3.5 h-3.5 animate-spin" />
                <span>Purging Vectors...</span>
              {:else}
                <Trash2 class="w-3.5 h-3.5" />
                <span>Delete & Purge Vector DB</span>
              {/if}
            </button>
          {:else}
            <button
              type="button"
              onclick={() => handleConfirm(false)}
              disabled={isDeleting || loadingReferences}
              class="px-4 py-2 rounded-lg text-xs font-medium bg-neutral-800 hover:bg-neutral-900 dark:bg-neutral-200 dark:hover:bg-white text-white dark:text-neutral-900 transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
            >
              {#if isDeleting}
                <Loader2 class="w-3.5 h-3.5 animate-spin" />
                <span>Removing...</span>
              {:else}
                <FolderMinus class="w-3.5 h-3.5" />
                <span>Remove from Collection Only</span>
              {/if}
            </button>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>
