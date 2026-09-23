<script lang="ts">
  import {
    X,
    FolderPlus,
    Building2,
    Users,
    User,
    ArrowRight,
    Lock,
    ShieldAlert
  } from '@lucide/svelte';
  import type { Collection, UserProfile } from '../types';
  import {
    canCreateCollection,
    getAllowedCollectionScopes,
    canCreateCollectionInScope
  } from '../utils/governance';

  interface Props {
    currentUser: UserProfile;
    onClose: () => void;
    onCreate: (newCol: Collection) => void;
  }

  let { currentUser, onClose, onCreate }: Props = $props();

  let allowedScopes = $derived(getAllowedCollectionScopes(currentUser));
  let canCreate = $derived(canCreateCollection(currentUser));
  let canScopeMine = $derived(allowedScopes.includes('mine'));
  let canScopeTeam = $derived(allowedScopes.includes('team'));
  let canScopeOrg = $derived(allowedScopes.includes('org'));

  let name = $state('');
  let description = $state('');
  let scope = $state<'mine' | 'team' | 'org'>('mine');
  // svelte-ignore state_referenced_locally
  let teamName = $state(currentUser.teamName || 'Platform Infrastructure');

  $effect(() => {
    // Ensure default selected scope is allowed
    if (allowedScopes.length > 0 && !allowedScopes.includes(scope)) {
      scope = allowedScopes[0];
    }
  });

  function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    if (!canCreate || !canCreateCollectionInScope(currentUser, scope)) return;

    const newCol: Collection = {
      id: `col-${Date.now()}`,
      name: name.trim(),
      description: description.trim() || 'No description provided.',
      scope,
      teamName: scope === 'team' ? teamName : undefined,
      createdBy: {
        name: currentUser.name,
        email: currentUser.email,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      documentCount: 0,
      totalChunks: 0,
      tags: [],
    };

    onCreate(newCol);
    onClose();
  }
</script>

<div class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none">
  <div class="w-full max-w-lg bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="p-1.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
          <FolderPlus class="w-4 h-4" />
        </div>
        <h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Create New Collection</h2>
      </div>

      <button
        type="button"
        onclick={onClose}
        class="p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 rounded transition-colors cursor-pointer"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Form -->
    <form onsubmit={handleSubmit} class="p-6 space-y-4 text-xs">
      {#if !canCreate}
        <div class="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-800 dark:text-amber-300 text-xs flex items-center gap-2">
          <Lock class="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <span>Your account role ({currentUser.systemRole.toUpperCase()}) is read-only. Creating collections requires contributor or administrator privileges.</span>
        </div>
      {/if}
      <!-- Collection Name -->
      <div>
        <label for="col-name" class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
          Collection Name <span class="text-rose-500">*</span>
        </label>
        <input
          id="col-name"
          type="text"
          required
          placeholder="e.g. Distributed Database Architecture 2026"
          bind:value={name}
          class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500 focus:bg-white dark:focus:bg-neutral-800/90"
        />
      </div>

      <!-- Description -->
      <div>
        <label for="col-desc" class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
          Description
        </label>
        <textarea
          id="col-desc"
          rows={3}
          placeholder="Describe the scope, systems covered, and intended audience..."
          bind:value={description}
          class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500 focus:bg-white dark:focus:bg-neutral-800/90 resize-none"
        ></textarea>
      </div>

      <!-- Scope Selection -->
      <div>
        <span class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1.5">
          Access Scope
        </span>
        <div class="grid grid-cols-3 gap-2">
          <button
            type="button"
            disabled={!canScopeMine}
            onclick={() => (scope = 'mine')}
            class="p-2.5 rounded-lg border text-left transition-all {!canScopeMine
              ? 'opacity-40 cursor-not-allowed bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              : scope === 'mine'
              ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
              : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer'}"
          >
            <div class="flex items-center justify-between font-medium mb-0.5">
              <div class="flex items-center gap-1.5">
                <User class="w-3.5 h-3.5" />
                <span>Personal</span>
              </div>
              {#if !canScopeMine}
                <Lock class="w-3 h-3 text-neutral-400" />
              {/if}
            </div>
            <div class="text-[10px] {scope === 'mine' ? 'text-blue-100' : 'text-neutral-400 dark:text-neutral-500'}">
              Private personal collection
            </div>
          </button>

          <button
            type="button"
            disabled={!canScopeTeam}
            onclick={() => (scope = 'team')}
            class="p-2.5 rounded-lg border text-left transition-all {!canScopeTeam
              ? 'opacity-40 cursor-not-allowed bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              : scope === 'team'
              ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
              : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer'}"
            title={!canScopeTeam ? 'Requires Team Lead or Admin role' : ''}
          >
            <div class="flex items-center justify-between font-medium mb-0.5">
              <div class="flex items-center gap-1.5">
                <Users class="w-3.5 h-3.5" />
                <span>Team</span>
              </div>
              {#if !canScopeTeam}
                <Lock class="w-3 h-3 text-neutral-400" />
              {/if}
            </div>
            <div class="text-[10px] {scope === 'team' ? 'text-blue-100' : 'text-neutral-400 dark:text-neutral-500'}">
              {canScopeTeam ? 'Shared with team members' : 'Requires Team Lead'}
            </div>
          </button>

          <button
            type="button"
            disabled={!canScopeOrg}
            onclick={() => (scope = 'org')}
            class="p-2.5 rounded-lg border text-left transition-all {!canScopeOrg
              ? 'opacity-40 cursor-not-allowed bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              : scope === 'org'
              ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
              : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer'}"
            title={!canScopeOrg ? 'Requires Admin or Owner role' : ''}
          >
            <div class="flex items-center justify-between font-medium mb-0.5">
              <div class="flex items-center gap-1.5">
                <Building2 class="w-3.5 h-3.5" />
                <span>Organization</span>
              </div>
              {#if !canScopeOrg}
                <Lock class="w-3 h-3 text-neutral-400" />
              {/if}
            </div>
            <div class="text-[10px] {scope === 'org' ? 'text-blue-100' : 'text-neutral-400 dark:text-neutral-500'}">
              {canScopeOrg ? 'Enterprise-wide shared' : 'Requires Admin/Owner'}
            </div>
          </button>
        </div>
      </div>

      <!-- If Team Scope, choose team name -->
      {#if scope === 'team'}
        <div>
          <label for="col-team" class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
            Team Identifier
          </label>
          <select
            id="col-team"
            bind:value={teamName}
            class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500"
          >
            <option value="Platform Infrastructure" class="dark:bg-neutral-800">Platform Infrastructure</option>
            <option value="Core AI Infrastructure" class="dark:bg-neutral-800">Core AI Infrastructure</option>
            <option value="Data Engineering" class="dark:bg-neutral-800">Data Engineering</option>
            <option value="SecOps & Compliance" class="dark:bg-neutral-800">SecOps &amp; Compliance</option>
            <option value="Frontend Architecture" class="dark:bg-neutral-800">Frontend Architecture</option>
          </select>
        </div>
      {/if}

      <!-- Footer Submit -->
      <div class="pt-4 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-end gap-2">
        <button
          type="button"
          onclick={onClose}
          class="px-3 py-1.5 text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 font-medium cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!name.trim() || !canCreate || !canCreateCollectionInScope(currentUser, scope)}
          class="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <span>Create Collection</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </form>
  </div>
</div>
