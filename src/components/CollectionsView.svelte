<script lang="ts">
  import {
    FolderKanban,
    Search,
    Plus,
    ArrowUpDown,
    Building2,
    Users,
    User,
    HardDrive,
    SlidersHorizontal,
    Sliders
  } from '@lucide/svelte';
  import type { Collection, ScopeType, TeamAllocationRecord, UserProfile } from '../types';
  import CollectionCard from './CollectionCard.svelte';
  import { canAccessAdmin, canCreateCollection } from '../utils/governance';

  interface Props {
    collections: Collection[];
    selectedScope: ScopeType;
    onSelectScope: (scope: ScopeType) => void;
    onSelectCollection: (collectionId: string) => void;
    onOpenNewCollection: () => void;
    onOpenAdmin?: () => void;
    currentUser?: UserProfile;
    teamAllocations?: TeamAllocationRecord[];
    onOpenTeamAllocationModal?: (teamRecord: TeamAllocationRecord) => void;
  }

  let {
    collections,
    selectedScope,
    onSelectScope,
    onSelectCollection,
    onOpenNewCollection,
    onOpenAdmin,
    currentUser,
    teamAllocations,
    onOpenTeamAllocationModal,
  }: Props = $props();

  let canAdmin = $derived(canAccessAdmin(currentUser));
  let canCreate = $derived(canCreateCollection(currentUser));
  let canManageQuotas = $derived(
    currentUser?.systemRole === 'owner' ||
    currentUser?.systemRole === 'admin' ||
    currentUser?.systemRole === 'team_lead' ||
    Boolean(currentUser?.isTeamLeader)
  );

  let searchQuery = $state('');
  let sharedSubFilter = $state<'all-shared' | 'org' | 'team'>('all-shared');
  let sortBy = $state<'updated' | 'name' | 'docs'>('updated');

  let filteredCollections = $derived.by(() => {
    let result = collections.filter((col) => {
      // 1. Scope filter
      if (selectedScope === 'mine' && col.scope !== 'mine') return false;
      if (selectedScope === 'org' && col.scope !== 'org') return false;
      if (selectedScope === 'team' && col.scope !== 'team') return false;

      // In 'Shared' general view, filter by sub-filter if set
      if (selectedScope === 'org' && sharedSubFilter === 'team' && col.scope !== 'team') return false;

      // 2. Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = col.name.toLowerCase().includes(q);
        const matchDesc = col.description.toLowerCase().includes(q);
        const matchTeam = col.teamName?.toLowerCase().includes(q);
        if (!matchName && !matchDesc && !matchTeam) return false;
      }

      return true;
    });

    return [...result].sort((a, b) => {
      if (sortBy === 'updated') {
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      }
      if (sortBy === 'docs') {
        return b.documentCount - a.documentCount;
      }
      return a.name.localeCompare(b.name);
    });
  });

  let orgCollections = $derived(filteredCollections.filter((c) => c.scope === 'org'));
  let teamCollections = $derived(filteredCollections.filter((c) => c.scope === 'team'));
  let mineCollections = $derived(filteredCollections.filter((c) => c.scope === 'mine'));
</script>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Top Header Bar -->
  <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-2">
      <FolderKanban class="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
      <h1 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">Collections</h1>
      <span class="text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums ml-1">
        ({filteredCollections.length})
      </span>
    </div>

    <div class="flex items-center gap-2.5">
      {#if onOpenAdmin && canAdmin}
        <button
          type="button"
          onclick={onOpenAdmin}
          class="flex items-center gap-1.5 px-3 py-1.5 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
          title="Configure token budgets, overlap windows, and re-indexing"
        >
          <SlidersHorizontal class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>Admin &amp; Ingestion</span>
        </button>
      {/if}
      {#if canCreate}
        <button
          type="button"
          onclick={onOpenNewCollection}
          class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>Create Collection</span>
        </button>
      {/if}
    </div>
  </div>

  <!-- Scope Navigation Bar & Filters -->
  <div class="px-6 pt-4 pb-3 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 space-y-3 shrink-0">
    <!-- Scope Tabs -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <!-- Segmented Control for Scope -->
      <div class="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200/80 dark:border-neutral-700">
        <button
          type="button"
          onclick={() => onSelectScope('mine')}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'mine'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        >
          <User class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>Personal</span>
        </button>

        <button
          type="button"
          onclick={() => {
            onSelectScope('org');
            sharedSubFilter = 'all-shared';
          }}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'org' || selectedScope === 'team'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        >
          <Building2 class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>Shared</span>
        </button>

        <button
          type="button"
          onclick={() => onSelectScope('all')}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'all'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        >
          <HardDrive class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>All</span>
        </button>
      </div>

      <!-- If inside Shared scope, show sub-groups toggle -->
      {#if selectedScope === 'org' || selectedScope === 'team'}
        <div class="flex items-center gap-1 text-xs">
          <span class="text-neutral-400 dark:text-neutral-500 mr-1 text-[11px]">Sub-group:</span>
          <button
            type="button"
            onclick={() => {
              onSelectScope('org');
              sharedSubFilter = 'all-shared';
            }}
            class="px-2.5 py-1 rounded text-xs transition-colors cursor-pointer {sharedSubFilter === 'all-shared'
              ? 'bg-blue-600 text-white font-medium shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
          >
            All Shared
          </button>
          <button
            type="button"
            onclick={() => {
              onSelectScope('org');
              sharedSubFilter = 'org';
            }}
            class="px-2.5 py-1 rounded text-xs transition-colors cursor-pointer {selectedScope === 'org' && sharedSubFilter === 'org'
              ? 'bg-blue-600 text-white font-medium shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
          >
            Organization
          </button>
          <button
            type="button"
            onclick={() => {
              onSelectScope('team');
              sharedSubFilter = 'team';
            }}
            class="px-2.5 py-1 rounded text-xs transition-colors cursor-pointer {selectedScope === 'team'
              ? 'bg-blue-600 text-white font-medium shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
          >
            Team
          </button>
        </div>
      {/if}

      <!-- Search & Sort -->
      <div class="flex items-center gap-2.5 ml-auto">
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Filter collections..."
            bind:value={searchQuery}
            class="pl-8 pr-3 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-600 w-48"
          />
        </div>

        <div class="flex items-center gap-1 text-xs text-neutral-600 dark:text-neutral-400">
          <ArrowUpDown class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
          <select
            bind:value={sortBy}
            class="bg-transparent text-xs text-neutral-700 dark:text-neutral-300 py-1 pr-2 border-0 focus:ring-0 cursor-pointer font-medium"
          >
            <option value="updated" class="dark:bg-neutral-800">Recently Updated</option>
            <option value="name" class="dark:bg-neutral-800">Alphabetical</option>
            <option value="docs" class="dark:bg-neutral-800">Document Count</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <!-- Main Collections Content Body -->
  <div class="flex-1 overflow-y-auto p-6">
    {#if filteredCollections.length === 0}
      <div class="h-64 border border-dashed border-neutral-300 dark:border-neutral-800 rounded-lg flex flex-col items-center justify-center text-center p-6 bg-white dark:bg-neutral-900">
        <FolderKanban class="w-10 h-10 text-neutral-400 dark:text-neutral-500 mb-2" />
        <h3 class="text-sm font-semibold text-neutral-800 dark:text-neutral-200">No collections found</h3>
        <p class="text-xs text-neutral-500 dark:text-neutral-400 max-w-sm mt-1 mb-4">
          {searchQuery
            ? `No collections matched "${searchQuery}". Try adjusting your search query or scope.`
            : 'No collections in this scope yet. Create a collection to organize ingested documents.'}
        </p>
        {#if canCreate}
          <button
            type="button"
            onclick={onOpenNewCollection}
            class="px-3.5 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 transition-colors cursor-pointer shadow-xs"
          >
            Create New Collection
          </button>
        {/if}
      </div>
    {:else}
      <div class="space-y-6">
        <!-- If All scope or Shared all-shared, display with clear section hierarchy -->
        {#if selectedScope === 'all' || (selectedScope === 'org' && sharedSubFilter === 'all-shared')}
          <!-- Organization Collections Group -->
          {#if orgCollections.length > 0}
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-1 border-b border-neutral-200 dark:border-neutral-800">
                <Building2 class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
                <h2 class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 uppercase tracking-wider">
                  Organization Collections
                </h2>
                <span class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">
                  ({orgCollections.length})
                </span>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {#each orgCollections as col (col.id)}
                  <CollectionCard
                    collection={col}
                    onselect={() => onSelectCollection(col.id)}
                  />
                {/each}
              </div>
            </div>
          {/if}

          <!-- Team Collections Group -->
          {#if teamCollections.length > 0}
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-1 border-b border-neutral-200 dark:border-neutral-800">
                <div class="flex items-center gap-2">
                  <Users class="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <h2 class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 uppercase tracking-wider">
                    Team Collections
                  </h2>
                  <span class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">
                    ({teamCollections.length})
                  </span>
                </div>

                {#if teamAllocations && onOpenTeamAllocationModal}
                  {@const targetTeam = teamAllocations.find(
                    (t) => t.teamName.toLowerCase() === (currentUser?.teamName || '').toLowerCase()
                  ) || teamAllocations[0]}
                  <button
                    type="button"
                    onclick={() => {
                      if (targetTeam) onOpenTeamAllocationModal(targetTeam);
                    }}
                    class="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium cursor-pointer"
                  >
                    <Sliders class="w-3.5 h-3.5" />
                    <span>Manage Team Quotas</span>
                  </button>
                {/if}
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {#each teamCollections as col (col.id)}
                  <CollectionCard
                    collection={col}
                    onselect={() => onSelectCollection(col.id)}
                  />
                {/each}
              </div>
            </div>
          {/if}

          <!-- Mine Group (if in All view) -->
          {#if selectedScope === 'all' && mineCollections.length > 0}
            <div class="space-y-3">
              <div class="flex items-center gap-2 pb-1 border-b border-neutral-200 dark:border-neutral-800">
                <User class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
                <h2 class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 uppercase tracking-wider">
                  Personal Collections
                </h2>
                <span class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">
                  ({mineCollections.length})
                </span>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {#each mineCollections as col (col.id)}
                  <CollectionCard
                    collection={col}
                    onselect={() => onSelectCollection(col.id)}
                  />
                {/each}
              </div>
            </div>
          {/if}
        {:else if selectedScope === 'team'}
          <div class="space-y-4">
            <div class="flex items-center justify-between pb-2 border-b border-neutral-200 dark:border-neutral-800">
              <div class="flex items-center gap-2">
                <Users class="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <h2 class="text-xs font-semibold text-neutral-800 dark:text-neutral-200 uppercase tracking-wider">
                  Team Collections ({filteredCollections.length})
                </h2>
              </div>

              {#if teamAllocations && onOpenTeamAllocationModal && canManageQuotas}
                {@const targetTeam = teamAllocations.find(
                  (t) => t.teamName.toLowerCase() === (currentUser?.teamName || '').toLowerCase()
                ) || teamAllocations[0]}
                <button
                  type="button"
                  onclick={() => {
                    if (targetTeam) onOpenTeamAllocationModal(targetTeam);
                  }}
                  class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60 border border-blue-200 dark:border-blue-900/60 text-blue-700 dark:text-blue-300 text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
                >
                  <Sliders class="w-3.5 h-3.5" />
                  <span>Manage Team Quotas</span>
                </button>
              {/if}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {#each filteredCollections as col (col.id)}
                <CollectionCard
                  collection={col}
                  onselect={() => onSelectCollection(col.id)}
                />
              {/each}
            </div>
          </div>
        {:else}
          <!-- Flat grid for Mine or Org-only views -->
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {#each filteredCollections as col (col.id)}
              <CollectionCard
                collection={col}
                onselect={() => onSelectCollection(col.id)}
              />
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>
