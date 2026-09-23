<script lang="ts">
  import {
    Home,
    FolderKanban,
    Search,
    Plus,
    User,
    Users,
    Building2,
    Layers,
    ChevronDown,
    ChevronRight,
    ShieldCheck,
    SlidersHorizontal,
    Shield,
    Lock,
    HardDrive,
    Sun,
    Moon
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, ScopeResourceAllocation, ScopeType, SystemRole, UserProfile } from '../types';
  import { formatBytes, getScopeUsedBytes } from '../utils/resourceUtils';
  import { canAccessAdmin, canCreateCollection } from '../utils/governance';

  interface Props {
    activeView: 'home' | 'collections' | 'search' | 'admin';
    onSelectView: (view: 'home' | 'collections' | 'search' | 'admin') => void;
    selectedScope: ScopeType;
    onSelectScope: (scope: ScopeType) => void;
    selectedCollectionId: string | null;
    onSelectCollection: (collectionId: string | null) => void;
    collections: Collection[];
    documents?: DocumentItem[];
    scopeResourceAllocation?: ScopeResourceAllocation;
    onOpenNewCollection: () => void;
    currentUser: UserProfile;
    onChangeUserRole?: (role: SystemRole) => void;
    isDarkMode?: boolean;
    onToggleDarkMode?: () => void;
  }

  let {
    activeView,
    onSelectView,
    selectedScope,
    onSelectScope,
    selectedCollectionId,
    onSelectCollection,
    collections,
    documents = [],
    scopeResourceAllocation,
    onOpenNewCollection,
    currentUser,
    onChangeUserRole,
    isDarkMode = false,
    onToggleDarkMode,
  }: Props = $props();

  let sharedExpanded = $state(true);

  let mineCollections = $derived(collections.filter((c) => c.scope === 'mine'));
  let orgCollections = $derived(collections.filter((c) => c.scope === 'org'));
  let teamCollections = $derived(collections.filter((c) => c.scope === 'team'));

  let personalUsedBytes = $derived(documents ? getScopeUsedBytes('mine', documents, collections) : 0);
  let personalCapGb = $derived(scopeResourceAllocation?.personalPerUserCapGb || 5);
  let personalCapBytes = $derived(personalCapGb * 1024 * 1024 * 1024);
  let personalPercent = $derived(Math.min(100, Math.round((personalUsedBytes / Math.max(1, personalCapBytes)) * 100)));

  let isOwnerOrAdmin = $derived(currentUser.systemRole === 'owner' || currentUser.systemRole === 'admin');
  let isTeamLead = $derived(currentUser.systemRole === 'team_lead' || Boolean(currentUser.isTeamLeader));
  let canAdmin = $derived(canAccessAdmin(currentUser));
  let canCreate = $derived(canCreateCollection(currentUser));
</script>

<aside class="w-60 h-screen bg-white dark:bg-neutral-900 text-neutral-800 dark:text-neutral-200 flex flex-col shrink-0 border-r border-neutral-200 dark:border-neutral-800 select-none transition-colors">
  <!-- Brand & Workspace Title -->
  <div class="h-14 px-4 flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800">
    <div class="flex items-center gap-2.5">
      <div class="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center text-white shrink-0 shadow-xs">
        <Layers class="w-4 h-4 text-white" />
      </div>
      <div class="font-semibold text-sm text-neutral-900 dark:text-neutral-100 tracking-tight">
        Nexus Knowledge
      </div>
    </div>

    {#if onToggleDarkMode}
      <button
        type="button"
        onclick={onToggleDarkMode}
        class="p-1.5 rounded-md text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-amber-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
        title={isDarkMode ? 'Switch to Light mode' : 'Switch to Dark mode'}
        aria-label="Toggle dark mode"
      >
        {#if isDarkMode}
          <Sun class="w-4 h-4 text-amber-400" />
        {:else}
          <Moon class="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
        {/if}
      </button>
    {/if}
  </div>

  <!-- New Collection Action -->
  {#if canCreate}
    <div class="p-3 border-b border-neutral-100 dark:border-neutral-800/80">
      <button
        type="button"
        onclick={onOpenNewCollection}
        class="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white hover:bg-blue-700 text-xs font-medium rounded-lg shadow-xs transition-colors cursor-pointer"
      >
        <Plus class="w-4 h-4" />
        <span>New Collection</span>
      </button>
    </div>
  {/if}

  <!-- Navigation Sections -->
  <div class="flex-1 overflow-y-auto p-2 space-y-4 text-xs">
    <!-- Top-Level Quick Links -->
    <div class="space-y-0.5">
      <!-- Home (Google Drive Style Landing) -->
      <button
        type="button"
        onclick={() => {
          onSelectCollection(null);
          onSelectView('home');
        }}
        class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md font-medium transition-colors cursor-pointer {activeView === 'home'
          ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 font-semibold'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
      >
        <div class="flex items-center gap-2.5">
          <Home class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
          <span>Home</span>
        </div>
      </button>

      <!-- Search -->
      <button
        type="button"
        onclick={() => onSelectView('search')}
        class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md font-medium transition-colors cursor-pointer {activeView === 'search'
          ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
      >
        <div class="flex items-center gap-2.5">
          <Search class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
          <span>Search</span>
        </div>
      </button>

      <!-- All Collections -->
      <button
        type="button"
        onclick={() => {
          onSelectCollection(null);
          onSelectScope('all');
          onSelectView('collections');
        }}
        class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md font-medium transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'all'
          ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
      >
        <div class="flex items-center gap-2.5">
          <FolderKanban class="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
          <span>All Collections</span>
        </div>
        <span class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">
          {collections.length}
        </span>
      </button>

      <!-- Admin & Ingestion Engine (Governance Protected) -->
      {#if canAdmin}
        <button
          type="button"
          onclick={() => onSelectView('admin')}
          class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md font-medium transition-colors cursor-pointer {activeView === 'admin'
            ? 'bg-blue-600 text-white font-semibold shadow-2xs'
            : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          title="Resource allocations, ingestion parameters, token budgets, and corpus re-indexing"
        >
          <div class="flex items-center gap-2.5">
            <SlidersHorizontal class="w-4 h-4 {activeView === 'admin' ? 'text-white' : 'text-neutral-500 dark:text-neutral-400'}" />
            <span>Admin &amp; Resources</span>
          </div>
          {#if isOwnerOrAdmin}
            <span
              class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-bold tracking-tight {activeView === 'admin'
                ? 'bg-blue-800 text-emerald-300'
                : 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300'}"
            >
              ADMIN
            </span>
          {:else if isTeamLead}
            <span
              class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-bold tracking-tight {activeView === 'admin'
                ? 'bg-blue-800 text-blue-200'
                : 'bg-blue-100 dark:bg-blue-950/70 text-blue-800 dark:text-blue-300'}"
            >
              LEAD
            </span>
          {/if}
        </button>
      {/if}
    </div>

    <!-- Scopes Divider -->
    <div class="space-y-1 pt-1">
      <div class="px-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
        Scopes
      </div>

      <!-- Personal Scope -->
      <button
        type="button"
        onclick={() => {
          onSelectView('collections');
          onSelectScope('mine');
          onSelectCollection(null);
        }}
        class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'mine'
          ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
      >
        <div class="flex items-center gap-2">
          <User class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>Personal</span>
        </div>
        <span class="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">
          {mineCollections.length}
        </span>
      </button>

      <!-- Shared Header Toggle -->
      <div class="pt-1">
        <button
          type="button"
          onclick={() => (sharedExpanded = !sharedExpanded)}
          class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 cursor-pointer"
        >
          <div class="flex items-center gap-2">
            <Users class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
            <span>Shared</span>
          </div>
          {#if sharedExpanded}
            <ChevronDown class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
          {:else}
            <ChevronRight class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
          {/if}
        </button>

        {#if sharedExpanded}
          <div class="pl-4 mt-0.5 space-y-0.5 border-l border-neutral-200 dark:border-neutral-800 ml-3">
            <!-- Organization -->
            <button
              type="button"
              onclick={() => {
                onSelectView('collections');
                onSelectScope('org');
                onSelectCollection(null);
              }}
              class="w-full flex items-center justify-between px-2 py-1 rounded text-xs transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'org'
                ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 font-medium'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'}"
            >
              <div class="flex items-center gap-1.5 truncate">
                <Building2 class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
                <span>Organization</span>
              </div>
              <span class="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">
                {orgCollections.length}
              </span>
            </button>

            <!-- Team -->
            <button
              type="button"
              onclick={() => {
                onSelectView('collections');
                onSelectScope('team');
                onSelectCollection(null);
              }}
              class="w-full flex items-center justify-between px-2 py-1 rounded text-xs transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'team'
                ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 font-medium'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'}"
            >
              <div class="flex items-center gap-1.5 truncate">
                <Users class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
                <span>Team</span>
              </div>
              <span class="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">
                {teamCollections.length}
              </span>
            </button>
          </div>
        {/if}
      </div>
    </div>

    <!-- Collections Quick List -->
    <div class="pt-2">
      <div class="px-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1">
        Collections
      </div>
      <div class="space-y-0.5 max-h-48 overflow-y-auto">
        {#each collections as col (col.id)}
          {@const isSelected = selectedCollectionId === col.id}
          <button
            type="button"
            onclick={() => {
              onSelectCollection(col.id);
              onSelectView('collections');
            }}
            class="w-full text-left px-2 py-1.5 rounded-md text-xs truncate transition-colors cursor-pointer {isSelected
              ? 'bg-blue-600 text-white font-medium shadow-2xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            {col.name}
          </button>
        {/each}
      </div>
    </div>
  </div>

  <!-- User Footer Profile & Role Switcher -->
  <div class="p-3 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50/70 dark:bg-neutral-900/90 space-y-2.5">
    {#if currentUser.systemRole !== 'viewer'}
      <!-- Personal Storage Quota Widget -->
      <div class="p-2 bg-white dark:bg-neutral-800/90 rounded-lg border border-neutral-200 dark:border-neutral-700/80 space-y-1 shadow-2xs">
        <div class="flex items-center justify-between text-[10px]">
          <span class="font-semibold text-neutral-600 dark:text-neutral-300 flex items-center gap-1">
            <HardDrive class="w-3 h-3 text-blue-600 dark:text-blue-400" />
            <span>Personal Storage</span>
          </span>
          <span class="font-mono text-neutral-500 dark:text-neutral-400 tabular-nums">
            {formatBytes(personalUsedBytes)} / {personalCapGb} GB
          </span>
        </div>
        <div class="w-full bg-neutral-100 dark:bg-neutral-700 h-1.5 rounded-full overflow-hidden">
          <div
            class="h-full transition-all duration-300 {personalPercent > 90 ? 'bg-rose-500' : 'bg-blue-600'}"
            style="width: {Math.max(2, personalPercent)}%"
          ></div>
        </div>
      </div>
    {:else}
      <div class="p-2 bg-neutral-100 dark:bg-neutral-800/60 rounded-lg border border-neutral-200 dark:border-neutral-700 text-[10px] text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
        <Lock class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
        <span>Read-Only Viewer Account</span>
      </div>
    {/if}

    {#if canAdmin}
      <button
        type="button"
        onclick={() => onSelectView('admin')}
        class="w-full flex items-center justify-between text-xs cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800/60 p-1.5 rounded-md transition-colors text-left"
        title="Click to open Admin & Resource Governance"
      >
        <div class="min-w-0">
          <div class="font-semibold text-neutral-900 dark:text-neutral-100 truncate flex items-center gap-1.5">
            <span>{currentUser.name}</span>
          </div>
          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 truncate">
            {currentUser.role}
          </div>
        </div>
        <span title="Role: {currentUser.systemRole.toUpperCase()}">
          {#if isOwnerOrAdmin}
            <ShieldCheck class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          {:else if isTeamLead}
            <Shield class="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
          {:else}
            <User class="w-4 h-4 text-neutral-400 dark:text-neutral-500 shrink-0" />
          {/if}
        </span>
      </button>
    {:else}
      <div class="w-full flex items-center justify-between text-xs p-1.5 rounded-md text-left">
        <div class="min-w-0">
          <div class="font-semibold text-neutral-900 dark:text-neutral-100 truncate flex items-center gap-1.5">
            <span>{currentUser.name}</span>
          </div>
          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 truncate">
            {currentUser.role}
          </div>
        </div>
        <span title="Role: {currentUser.systemRole.toUpperCase()}">
          <User class="w-4 h-4 text-neutral-400 dark:text-neutral-500 shrink-0" />
        </span>
      </div>
    {/if}

    <!-- Quick RBAC Switcher & Theme Pill -->
    <div class="pt-1 flex items-center justify-between gap-1 text-[10px]">
      <span class="text-neutral-400 dark:text-neutral-500">Access:</span>
      {#if onChangeUserRole}
        <select
          value={currentUser.systemRole}
          onchange={(e) => onChangeUserRole((e.currentTarget as HTMLSelectElement).value as SystemRole)}
          class="bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded px-1.5 py-0.5 text-[10px] font-mono font-medium text-neutral-800 dark:text-neutral-200 cursor-pointer focus:outline-hidden focus:border-blue-500"
        >
          <option value="owner">owner (full)</option>
          <option value="admin">admin</option>
          <option value="team_lead">team lead</option>
          <option value="member">member</option>
          <option value="viewer">viewer</option>
        </select>
      {/if}
    </div>
  </div>
</aside>
