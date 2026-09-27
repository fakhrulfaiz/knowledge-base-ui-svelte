<script lang="ts">
  import {
    X,
    FolderPlus,
    Building2,
    Users,
    Briefcase,
    ArrowRight,
    Lock
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
  let canScopeProject = $derived(allowedScopes.includes('project'));
  let canScopeTeam = $derived(allowedScopes.includes('team'));
  let canScopeOrg = $derived(allowedScopes.includes('org'));

  let name = $state('');
  let description = $state('');
  let scope = $state<'org' | 'team' | 'project' | 'mine'>('project');
  let teamName = $state('');
  let projectName = $state('Core Modernization');

  $effect(() => {
    if (!teamName) {
      teamName = currentUser?.teamName || 'Platform Infrastructure';
    }
    if (allowedScopes.length > 0 && !allowedScopes.includes(scope)) {
      scope = allowedScopes[0];
    }
  });

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    if (!canCreate || !canCreateCollectionInScope(currentUser, scope)) return;

    const colId = `col-${Date.now()}`;
    const cleanName = name.trim();

    const payload = {
      id: colId,
      name: cleanName,
      description: description.trim() || 'No description provided.',
      scope,
      teamName: scope === 'team' ? teamName.trim() : undefined,
      projectName: scope === 'project' ? projectName.trim() : undefined,
      allocatedGb: scope === 'org' ? 50 : scope === 'team' ? 30 : 15
    };

    try {
      const res = await fetch('http://localhost:8080/api/collections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const created = await res.json();
        onCreate(created);
        onClose();
        return;
      }
    } catch (err) {
      console.warn('Backend call failed, creating locally:', err);
    }

    const newCol: Collection = {
      id: colId,
      name: cleanName,
      description: description.trim() || 'No description provided.',
      scope,
      teamName: scope === 'team' ? teamName.trim() : undefined,
      projectName: scope === 'project' ? projectName.trim() : undefined,
      allocatedGb: scope === 'org' ? 50 : scope === 'team' ? 30 : 15,
      createdBy: {
        name: currentUser.name,
        email: currentUser.email,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      documentCount: 0,
      totalChunks: 0,
      tags: [scope.toUpperCase(), scope === 'team' ? teamName : scope === 'project' ? projectName : 'Global'],
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
        <div class="p-1.5 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
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
          class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-blue-500 focus:bg-white dark:focus:bg-neutral-800/90"
        />
      </div>

      <!-- Description -->
      <div>
        <label for="col-desc" class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
          Description
        </label>
        <textarea
          id="col-desc"
          rows={2}
          placeholder="Describe the collection domain, systems covered, and intended audience..."
          bind:value={description}
          class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-blue-500 focus:bg-white dark:focus:bg-neutral-800/90 resize-none"
        ></textarea>
      </div>

      <!-- Scope Selection: Org, Team, Project -->
      <div>
        <span class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1.5">
          Governance Scope
        </span>
        <div class="grid grid-cols-3 gap-2">
          <!-- Org -->
          <button
            type="button"
            disabled={!canScopeOrg}
            onclick={() => (scope = 'org')}
            class="p-2.5 rounded-lg border text-left transition-all {!canScopeOrg
              ? 'opacity-40 cursor-not-allowed bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              : scope === 'org'
              ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
              : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer'}"
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
              Enterprise-wide corpus
            </div>
          </button>

          <!-- Team -->
          <button
            type="button"
            disabled={!canScopeTeam}
            onclick={() => (scope = 'team')}
            class="p-2.5 rounded-lg border text-left transition-all {!canScopeTeam
              ? 'opacity-40 cursor-not-allowed bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              : scope === 'team'
              ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
              : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer'}"
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
              Shared team repository
            </div>
          </button>

          <!-- Project -->
          <button
            type="button"
            disabled={!canScopeProject}
            onclick={() => (scope = 'project')}
            class="p-2.5 rounded-lg border text-left transition-all {!canScopeProject
              ? 'opacity-40 cursor-not-allowed bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              : scope === 'project'
              ? 'bg-blue-600 text-white border-blue-600 shadow-xs cursor-pointer'
              : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer'}"
          >
            <div class="flex items-center justify-between font-medium mb-0.5">
              <div class="flex items-center gap-1.5">
                <Briefcase class="w-3.5 h-3.5" />
                <span>Project</span>
              </div>
              {#if !canScopeProject}
                <Lock class="w-3 h-3 text-neutral-400" />
              {/if}
            </div>
            <div class="text-[10px] {scope === 'project' ? 'text-blue-100' : 'text-neutral-400 dark:text-neutral-500'}">
              Dedicated project workspace
            </div>
          </button>
        </div>
      </div>

      <!-- Scope Specific Inputs -->
      {#if scope === 'team'}
        <div>
          <label for="col-team" class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
            Team Name
          </label>
          <input
            id="col-team"
            type="text"
            required
            bind:value={teamName}
            class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 focus:outline-hidden focus:border-blue-500"
          />
        </div>
      {:else if scope === 'project'}
        <div>
          <label for="col-proj" class="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
            Project Name
          </label>
          <input
            id="col-proj"
            type="text"
            required
            bind:value={projectName}
            class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 focus:outline-hidden focus:border-blue-500"
          />
        </div>
      {/if}

      <!-- Footer Buttons -->
      <div class="pt-2 flex items-center justify-end gap-2 border-t border-neutral-100 dark:border-neutral-800">
        <button
          type="button"
          onclick={onClose}
          class="px-3 py-1.5 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md text-neutral-700 dark:text-neutral-300 font-medium transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!canCreate || !name.trim()}
          class="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <span>Create Collection</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </form>
  </div>
</div>
