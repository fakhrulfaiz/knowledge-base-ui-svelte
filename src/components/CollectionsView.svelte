<script lang="ts">
  import {
    FolderKanban,
    Search,
    Plus,
    ArrowUpDown,
    SlidersHorizontal,
    Sliders,
    Building2,
    Users,
    Briefcase
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
    onDeleteCollection?: (col: Collection) => void;
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
    onDeleteCollection,
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
  let sortBy = $state<'updated' | 'name' | 'docs'>('updated');

  let filteredCollections = $derived.by(() => {
    let result = collections.filter((col) => {
      // Scope filter
      if (selectedScope === 'org' && col.scope !== 'org') return false;
      if (selectedScope === 'team' && col.scope !== 'team') return false;
      if (selectedScope === 'project' && col.scope !== 'project') return false;

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = col.name.toLowerCase().includes(q);
        const matchDesc = col.description.toLowerCase().includes(q);
        const matchTeam = col.teamName?.toLowerCase().includes(q);
        const matchProj = col.projectName?.toLowerCase().includes(q);
        if (!matchName && !matchDesc && !matchTeam && !matchProj) return false;
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
          class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Collection</span>
        </button>
      {/if}
    </div>
  </div>

  <!-- Filter Bar: All, Org, Team, Project -->
  <div class="px-6 py-3 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shrink-0">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <!-- Quick Filter Pills -->
      <div class="flex items-center gap-1.5">
        <div class="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200/80 dark:border-neutral-700">
          <button
            type="button"
            onclick={() => onSelectScope('all')}
            class="px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'all'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            All
          </button>
          <button
            type="button"
            onclick={() => onSelectScope('org')}
            class="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'org'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Building2 class="w-3 h-3" />
            <span>Organization</span>
          </button>
          <button
            type="button"
            onclick={() => onSelectScope('team')}
            class="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'team'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Users class="w-3 h-3" />
            <span>Team</span>
          </button>
          <button
            type="button"
            onclick={() => onSelectScope('project')}
            class="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer {selectedScope === 'project'
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <Briefcase class="w-3 h-3" />
            <span>Project</span>
          </button>
        </div>

        {#if teamAllocations && onOpenTeamAllocationModal && canManageQuotas}
          {@const targetTeam = teamAllocations.find(
            (t) => t.teamName.toLowerCase() === (currentUser?.teamName || '').toLowerCase()
          ) || teamAllocations[0]}
          {#if targetTeam}
            <button
              type="button"
              onclick={() => onOpenTeamAllocationModal(targetTeam)}
              class="flex items-center gap-1.5 px-2.5 py-1 text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors cursor-pointer"
            >
              <Sliders class="w-3.5 h-3.5" />
              <span>Quotas</span>
            </button>
          {/if}
        {/if}
      </div>

      <!-- Search & Sort -->
      <div class="flex items-center gap-2.5 ml-auto">
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search collections..."
            bind:value={searchQuery}
            class="pl-8 pr-3 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-600 w-48"
          />
        </div>

        <div class="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
          <ArrowUpDown class="w-3.5 h-3.5" />
          <select
            bind:value={sortBy}
            class="bg-transparent border-0 text-xs text-neutral-700 dark:text-neutral-300 font-medium focus:outline-hidden cursor-pointer"
          >
            <option value="updated">Recent</option>
            <option value="name">Name</option>
            <option value="docs">Doc count</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <!-- Content Grid -->
  <div class="flex-1 overflow-y-auto p-6 custom-scrollbar">
    {#if filteredCollections.length === 0}
      <div class="h-64 flex flex-col items-center justify-center text-neutral-400 dark:text-neutral-500">
        <FolderKanban class="w-10 h-10 stroke-[1.5] mb-2 opacity-60" />
        <p class="text-xs">No collections found in this scope</p>
        {#if canCreate}
          <button
            type="button"
            onclick={onOpenNewCollection}
            class="mt-3 text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium cursor-pointer"
          >
            Create your first collection
          </button>
        {/if}
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each filteredCollections as col (col.id)}
          <CollectionCard
            collection={col}
            {currentUser}
            onselect={() => onSelectCollection(col.id)}
            onDelete={onDeleteCollection}
          />
        {/each}
      </div>
    {/if}
  </div>
</div>
