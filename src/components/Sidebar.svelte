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
    ChevronLeft,
    ShieldCheck,
    SlidersHorizontal,
    Shield,
    Lock,
    HardDrive,
    Sun,
    Moon,
    X
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
    isMobileOpen?: boolean;
    onCloseMobile?: () => void;
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
    isMobileOpen = false,
    onCloseMobile,
  }: Props = $props();

  // Responsive default: collapse on smaller screens, expanded on larger screens
  function getInitialCollapsed(): boolean {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 768;
    }
    return false;
  }

  let isCollapsed = $state(getInitialCollapsed());
  let sharedExpanded = $state(true);

  // When mobile drawer is open, always show full navigation
  let showExpanded = $derived(!isCollapsed || isMobileOpen);

  function handleNavAction(action: () => void) {
    action();
    onCloseMobile?.();
  }

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

<!-- Mobile Overlay Backdrop -->
{#if isMobileOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 bg-neutral-950/60 backdrop-blur-xs z-40 md:hidden"
    onclick={onCloseMobile}
  ></div>
{/if}

<aside
  class="h-screen bg-white dark:bg-neutral-900 text-neutral-800 dark:text-neutral-200 flex flex-col shrink-0 border-r border-neutral-200 dark:border-neutral-800 select-none transition-all duration-300 ease-in-out
    fixed inset-y-0 left-0 z-50 md:static md:z-auto
    {isMobileOpen ? 'translate-x-0 w-72 max-w-[85vw] shadow-2xl' : '-translate-x-full md:translate-x-0'}
    {!showExpanded ? 'md:w-16' : 'md:w-64 lg:w-72'}
    overflow-hidden"
>
  <!-- Brand & Workspace Title / Expand-Collapse & Theme Toggle -->
  <div class="h-13 px-3 flex items-center {!showExpanded ? 'justify-center' : 'justify-between'} border-b border-neutral-200 dark:border-neutral-800 shrink-0">
    {#if showExpanded}
      <div class="flex items-center gap-2 min-w-0">
        <div class="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white shrink-0 shadow-xs">
          <Layers class="w-4 h-4 text-white" />
        </div>
        <div class="font-semibold text-sm sm:text-base text-neutral-900 dark:text-neutral-100 tracking-tight truncate">
          Cognify Knowledge
        </div>
      </div>

      <div class="flex items-center gap-1 shrink-0">
        <!-- Sleek Icon-only Dark/Light Mode Toggle in the Header! Takes 0 vertical height from the footer -->
        {#if onToggleDarkMode}
          <button
            type="button"
            onclick={onToggleDarkMode}
            class="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
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

        <!-- Desktop Collapse Button -->
        <button
          type="button"
          onclick={() => (isCollapsed = true)}
          class="hidden md:inline-flex p-1.5 rounded-lg text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>

        <!-- Mobile Close Button -->
        {#if onCloseMobile}
          <button
            type="button"
            onclick={onCloseMobile}
            class="md:hidden p-1.5 rounded-lg text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
            title="Close navigation"
            aria-label="Close navigation"
          >
            <X class="w-4.5 h-4.5" />
          </button>
        {/if}
      </div>
    {:else}
      <div class="flex flex-col items-center gap-1 py-1">
        <button
          type="button"
          onclick={() => (isCollapsed = false)}
          class="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          title="Expand sidebar"
          aria-label="Expand sidebar"
        >
          <ChevronRight class="w-4.5 h-4.5" />
        </button>
        {#if onToggleDarkMode}
          <button
            type="button"
            onclick={onToggleDarkMode}
            class="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
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
    {/if}
  </div>

  <!-- New Collection Action -->
  {#if canCreate}
    <div class="{!showExpanded ? 'p-2 flex justify-center' : 'p-2.5 sm:p-3'} border-b border-neutral-100 dark:border-neutral-800/80 shrink-0">
      {#if showExpanded}
        <button
          type="button"
          onclick={() => handleNavAction(onOpenNewCollection)}
          class="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white hover:bg-blue-700 text-xs sm:text-sm font-medium rounded-xl shadow-xs transition-colors cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          <span>New Collection</span>
        </button>
      {:else}
        <button
          type="button"
          onclick={() => handleNavAction(onOpenNewCollection)}
          class="w-9 h-9 flex items-center justify-center bg-blue-600 text-white hover:bg-blue-700 rounded-xl shadow-xs transition-colors cursor-pointer"
          title="New Collection"
          aria-label="New Collection"
        >
          <Plus class="w-4.5 h-4.5" />
        </button>
      {/if}
    </div>
  {/if}
  <!-- Navigation Sections: Primary navigation is fixed with NO scrollbar, only Collections list can scroll -->
  <div class="flex-1 flex flex-col min-h-0 {!showExpanded ? 'p-2 space-y-2' : 'p-2.5 sm:p-3 space-y-1.5 sm:space-y-2'} text-xs sm:text-sm overflow-hidden">
    <!-- Top-Level Quick Links (Home, Search, All Collections, Admin) - Fixed in view (shrink-0) -->
    <div class="space-y-0.5 shrink-0">
      <!-- Home (Google Drive Style Landing) -->
      <button
        type="button"
        onclick={() =>
          handleNavAction(() => {
            onSelectCollection(null);
            onSelectView('home');
          })}
        class="w-full flex items-center {!showExpanded ? 'justify-center p-2' : 'justify-between px-2.5 sm:px-3 py-1.5'} rounded-xl font-medium transition-colors cursor-pointer {activeView === 'home'
          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        title="Home"
      >
        <div class="flex items-center gap-2.5">
          <Home class="w-4 h-4 sm:w-4.5 sm:h-4.5 {activeView === 'home' ? 'text-blue-600 dark:text-blue-400' : 'text-neutral-500 dark:text-neutral-400'}" />
          {#if showExpanded}
            <span>Home</span>
          {/if}
        </div>
      </button>

      <!-- Search -->
      <button
        type="button"
        onclick={() => handleNavAction(() => onSelectView('search'))}
        class="w-full flex items-center {!showExpanded ? 'justify-center p-2' : 'justify-between px-2.5 sm:px-3 py-1.5'} rounded-xl font-medium transition-colors cursor-pointer {activeView === 'search'
          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        title="Semantic Passage Search"
      >
        <div class="flex items-center gap-2.5">
          <Search class="w-4 h-4 sm:w-4.5 sm:h-4.5 {activeView === 'search' ? 'text-blue-600 dark:text-blue-400' : 'text-neutral-500 dark:text-neutral-400'}" />
          {#if showExpanded}
            <span>Search</span>
          {/if}
        </div>
      </button>

      <!-- All Collections -->
      <button
        type="button"
        onclick={() =>
          handleNavAction(() => {
            onSelectCollection(null);
            onSelectScope('all');
            onSelectView('collections');
          })}
        class="w-full flex items-center {!showExpanded ? 'justify-center p-2' : 'justify-between px-2.5 sm:px-3 py-1.5'} rounded-xl font-medium transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'all'
          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        title="All Collections"
      >
        <div class="flex items-center gap-2">
          <FolderKanban class="w-4 h-4 sm:w-4.5 sm:h-4.5 {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'all' ? 'text-blue-600 dark:text-blue-400' : 'text-neutral-500 dark:text-neutral-400'}" />
          {#if showExpanded}
            <span>All Collections</span>
            <span class="text-[11px] sm:text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">({collections.length})</span>
          {/if}
        </div>
      </button>

      <!-- Admin & Ingestion Engine (Governance Protected) -->
      {#if canAdmin}
        <button
          type="button"
          onclick={() => handleNavAction(() => onSelectView('admin'))}
          class="w-full flex items-center {!showExpanded ? 'justify-center p-2' : 'justify-between px-2.5 sm:px-3 py-1.5'} rounded-xl font-medium transition-colors cursor-pointer {activeView === 'admin'
            ? 'bg-blue-600 text-white font-semibold shadow-2xs'
            : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          title="Admin & Resources"
        >
          <div class="flex items-center gap-2.5">
            <SlidersHorizontal class="w-4 h-4 sm:w-4.5 sm:h-4.5 {activeView === 'admin' ? 'text-white' : 'text-neutral-500 dark:text-neutral-400'}" />
            {#if showExpanded}
              <span>Admin &amp; Resources</span>
            {/if}
          </div>
          {#if showExpanded}
            {#if isOwnerOrAdmin}
              <span
                class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-tight {activeView === 'admin'
                  ? 'bg-blue-800 text-emerald-300'
                  : 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300'}"
              >
                ADMIN
              </span>
            {:else if isTeamLead}
              <span
                class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-tight {activeView === 'admin'
                  ? 'bg-blue-800 text-blue-200'
                  : 'bg-blue-100 dark:bg-blue-950/70 text-blue-800 dark:text-blue-300'}"
              >
                LEAD
              </span>
            {/if}
          {/if}
        </button>
      {/if}
    </div>

    <!-- Scopes Section - Fixed in view (shrink-0) -->
    <div class="space-y-0.5 pt-1.5 border-t border-neutral-100 dark:border-neutral-800/80 shrink-0">
      {#if showExpanded}
        <div class="px-2 text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-0.5">
          Scopes
        </div>
      {/if}

      <!-- Personal Scope -->
      <button
        type="button"
        onclick={() =>
          handleNavAction(() => {
            onSelectView('collections');
            onSelectCollection(null);
            onSelectScope('mine');
          })}
        class="w-full flex items-center {!showExpanded ? 'justify-center p-2' : 'justify-between px-2.5 sm:px-3 py-1.5'} rounded-xl font-medium transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'mine'
          ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
        title="Personal Scope"
      >
        <div class="flex items-center gap-2">
          <User class="w-4 h-4 sm:w-4.5 sm:h-4.5 {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'mine' ? 'text-blue-600 dark:text-blue-400' : 'text-neutral-500 dark:text-neutral-400'}" />
          {#if showExpanded}
            <span>Personal</span>
            <span class="text-[11px] sm:text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">({mineCollections.length})</span>
          {/if}
        </div>
      </button>

      <!-- Shared Scopes Header / Team & Org Folders -->
      <button
        type="button"
        onclick={() => {
          if (showExpanded) {
            sharedExpanded = !sharedExpanded;
          } else {
            handleNavAction(() => {
              onSelectView('collections');
              onSelectCollection(null);
              onSelectScope('team');
            });
          }
        }}
        class="w-full flex items-center {!showExpanded ? 'justify-center p-2' : 'justify-between px-2.5 sm:px-3 py-1.5'} rounded-xl font-medium transition-colors cursor-pointer text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100"
        title="Shared Knowledge (Team & Org)"
      >
        <div class="flex items-center gap-2">
          <Users class="w-4 h-4 sm:w-4.5 sm:h-4.5 text-neutral-500 dark:text-neutral-400" />
          {#if showExpanded}
            <span>Shared</span>
            <span class="text-[11px] sm:text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">({teamCollections.length + orgCollections.length})</span>
          {/if}
        </div>
        {#if showExpanded}
          <div class="flex items-center">
            {#if sharedExpanded}
              <ChevronDown class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-neutral-400 dark:text-neutral-500" />
            {:else}
              <ChevronRight class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-neutral-400 dark:text-neutral-500" />
            {/if}
          </div>
        {/if}
      </button>

      {#if sharedExpanded && showExpanded}
        <!-- Shared Sub-items: Organization & Team -->
        <div class="pl-4 space-y-0.5 pt-0.5">
          <!-- Organization Sub-scope -->
          <button
            type="button"
            onclick={() =>
              handleNavAction(() => {
                onSelectView('collections');
                onSelectCollection(null);
                onSelectScope('org');
              })}
            class="w-full flex items-center justify-between px-2.5 sm:px-3 py-1.5 rounded-lg text-xs sm:text-sm transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'org'
              ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <div class="flex items-center gap-2">
              <Building2 class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-neutral-400 dark:text-neutral-500" />
              <span>Organization</span>
              <span class="text-[11px] sm:text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">({orgCollections.length})</span>
            </div>
          </button>

          <!-- Team Sub-scope -->
          <button
            type="button"
            onclick={() =>
              handleNavAction(() => {
                onSelectView('collections');
                onSelectCollection(null);
                onSelectScope('team');
              })}
            class="w-full flex items-center justify-between px-2.5 sm:px-3 py-1.5 rounded-lg text-xs sm:text-sm transition-colors cursor-pointer {activeView === 'collections' && selectedCollectionId === null && selectedScope === 'team'
              ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
          >
            <div class="flex items-center gap-2">
              <Users class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-neutral-400 dark:text-neutral-500" />
              <span>Team</span>
              <span class="text-[11px] sm:text-xs text-neutral-400 dark:text-neutral-500 font-mono tabular-nums">({teamCollections.length})</span>
            </div>
          </button>
        </div>
      {/if}
    </div>

    <!-- Collections List - Dedicated Scrollable Container with Custom Pretty Scrollbar -->
    {#if showExpanded}
      <div class="flex-1 flex flex-col min-h-0 pt-1.5 border-t border-neutral-100 dark:border-neutral-800/80">
        <div class="px-2 text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1 flex items-center justify-between shrink-0">
          <span>Collections</span>
          <span class="text-[10px] font-mono text-neutral-400 dark:text-neutral-500 tabular-nums">
            {collections.length}
          </span>
        </div>
        <div class="flex-1 min-h-0 overflow-y-auto pr-1 space-y-0.5 custom-scrollbar">
          {#each collections as col (col.id)}
            {@const isSelected = selectedCollectionId === col.id}
            <button
              type="button"
              onclick={() => handleNavAction(() => onSelectCollection(col.id))}
              class="w-full text-left px-2 sm:px-2.5 py-1.5 rounded-lg text-xs sm:text-sm truncate transition-colors cursor-pointer {isSelected
                ? 'bg-blue-600 text-white font-medium shadow-2xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800/60 hover:text-neutral-900 dark:hover:text-neutral-100'}"
              title={col.name}
            >
              {col.name}
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- User Footer Area: Compact, space-saving design that scales gracefully -->
  <div class="p-2 sm:p-2.5 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50/70 dark:bg-neutral-900/90 space-y-1.5 shrink-0">
    <!-- Storage Quota Widget -->
    {#if showExpanded}
      {#if currentUser.systemRole !== 'viewer'}
        <div class="p-1.5 sm:p-2 bg-white dark:bg-neutral-800/90 rounded-lg border border-neutral-200 dark:border-neutral-700/80 space-y-1 shadow-2xs">
          <div class="flex items-center justify-between text-xs">
            <span class="font-medium text-neutral-700 dark:text-neutral-300 flex items-center gap-1.5 text-[11px]">
              <HardDrive class="w-3 h-3 text-blue-600 dark:text-blue-400" />
              <span>Personal Storage</span>
            </span>
            <span class="font-mono text-neutral-500 dark:text-neutral-400 text-[10px] tabular-nums">
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
        <div class="p-1.5 bg-neutral-100 dark:bg-neutral-800/60 rounded-lg border border-neutral-200 dark:border-neutral-700 text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
          <Lock class="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
          <span>Read-Only Viewer</span>
        </div>
      {/if}
    {:else}
      <div
        class="w-9 h-9 mx-auto flex items-center justify-center rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 cursor-default"
        title="Personal Storage: {formatBytes(personalUsedBytes)} / {personalCapGb} GB ({personalPercent}%)"
      >
        <HardDrive class="w-4 h-4 text-blue-600 dark:text-blue-400" />
      </div>
    {/if}

    <!-- User Profile & Access Switcher -->
    {#if showExpanded}
      <div class="pt-0.5 space-y-1">
        {#if canAdmin}
          <button
            type="button"
            onclick={() => handleNavAction(() => onSelectView('admin'))}
            class="w-full flex items-center justify-between text-xs cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800/60 p-1 sm:p-1.5 rounded-lg transition-colors text-left"
            title="Click to open Admin & Resource Governance"
          >
            <div class="min-w-0">
              <div class="font-semibold text-xs sm:text-sm text-neutral-900 dark:text-neutral-100 truncate">
                {currentUser.name}
              </div>
              <div class="text-[10px] text-neutral-500 dark:text-neutral-400 truncate">
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
          <div class="w-full flex items-center justify-between text-xs p-1 sm:p-1.5 rounded-lg text-left">
            <div class="min-w-0">
              <div class="font-semibold text-xs sm:text-sm text-neutral-900 dark:text-neutral-100 truncate">
                {currentUser.name}
              </div>
              <div class="text-[10px] text-neutral-500 dark:text-neutral-400 truncate">
                {currentUser.role}
              </div>
            </div>
            <span title="Role: {currentUser.systemRole.toUpperCase()}">
              <User class="w-4 h-4 text-neutral-400 dark:text-neutral-500 shrink-0" />
            </span>
          </div>
        {/if}

        <!-- Quick RBAC Role Switcher -->
        {#if onChangeUserRole}
          <div class="flex items-center justify-between gap-1 text-[11px] px-1">
            <span class="text-neutral-400 dark:text-neutral-500 font-medium">Access:</span>
            <select
              value={currentUser.systemRole}
              onchange={(e) => onChangeUserRole((e.currentTarget as HTMLSelectElement).value as SystemRole)}
              class="bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded px-1.5 py-0.5 text-[11px] font-mono text-neutral-800 dark:text-neutral-200 cursor-pointer focus:outline-hidden"
            >
              <option value="owner">owner</option>
              <option value="admin">admin</option>
              <option value="team_lead">lead</option>
              <option value="member">member</option>
              <option value="viewer">viewer</option>
            </select>
          </div>
        {/if}
      </div>
    {:else}
      <!-- Collapsed User Avatar -->
      <div
        class="w-9 h-9 mx-auto rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 font-bold text-xs flex items-center justify-center border border-blue-500/40 cursor-default"
        title="{currentUser.name} ({currentUser.role} · {currentUser.systemRole.toUpperCase()})"
      >
        {currentUser.avatarText || 'ER'}
      </div>
    {/if}
  </div>
</aside>
