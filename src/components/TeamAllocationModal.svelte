<script lang="ts">
  import {
    X,
    Users,
    CheckCircle2,
    AlertTriangle,
    Layers,
    ArrowRight,
    ShieldAlert,
    Info,
    Plus,
    Trash2
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, TeamAllocationRecord, UserProfile } from '../types';
  import { formatBytes, getCollectionUsedBytes } from '../utils/resourceUtils';

  interface Props {
    teamRecord: TeamAllocationRecord;
    collections: Collection[];
    documents: DocumentItem[];
    currentUser: UserProfile;
    onClose: () => void;
    onSaveAllocations: (updatedRecord: TeamAllocationRecord) => void;
  }

  let {
    teamRecord,
    collections,
    documents,
    currentUser,
    onClose,
    onSaveAllocations,
  }: Props = $props();

  function buildInitialAllocations() {
    const teamCols = collections.filter(
      (c) => c.scope === 'team' && c.teamName?.toLowerCase() === teamRecord.teamName.toLowerCase()
    );
    const existingMap = new Map(teamRecord.collectionAllocations.map((a) => [a.collectionId, a]));
    const list = [...teamRecord.collectionAllocations];

    teamCols.forEach((col) => {
      if (!existingMap.has(col.id)) {
        list.push({
          collectionId: col.id,
          collectionName: col.name,
          allocatedGb: col.allocatedGb || 10,
        });
      }
    });

    return list;
  }

  let allocations = $state(buildInitialAllocations());
  let newColName = $state('');
  let newColGb = $state<number>(10);
  let showAddCustom = $state(false);
  let saveSuccess = $state(false);

  let canManage = $derived(
    currentUser.systemRole === 'owner' ||
    currentUser.systemRole === 'admin' ||
    currentUser.systemRole === 'team_lead' ||
    Boolean(currentUser.isTeamLeader)
  );

  let totalTeamCapGb = $derived(teamRecord.allocatedGb);
  let currentTotalAllocatedGb = $derived(
    allocations.reduce((acc, a) => acc + (Number(a.allocatedGb) || 0), 0)
  );
  let unallocatedBufferGb = $derived(totalTeamCapGb - currentTotalAllocatedGb);
  let isOverAllocated = $derived(unallocatedBufferGb < 0);

  function handleAllocationChange(collectionId: string, val: number) {
    const clamped = Math.max(0, Math.min(totalTeamCapGb * 2, val));
    allocations = allocations.map((item) =>
      item.collectionId === collectionId ? { ...item, allocatedGb: clamped } : item
    );
  }

  function handleAddCustomAllocation() {
    if (!newColName.trim()) return;
    const newEntry = {
      collectionId: `col-custom-${Date.now()}`,
      collectionName: newColName.trim(),
      allocatedGb: Math.max(1, newColGb),
    };
    allocations = [...allocations, newEntry];
    newColName = '';
    newColGb = 10;
    showAddCustom = false;
  }

  function handleRemoveAllocation(collectionId: string) {
    allocations = allocations.filter((a) => a.collectionId !== collectionId);
  }

  function handleSave() {
    const updated: TeamAllocationRecord = {
      ...teamRecord,
      collectionAllocations: allocations,
    };
    onSaveAllocations(updated);
    saveSuccess = true;
    setTimeout(() => {
      saveSuccess = false;
      onClose();
    }, 1200);
  }
</script>

<div class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-150 select-none">
  <div class="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-800 w-full max-w-2xl flex flex-col max-h-[90vh] overflow-hidden text-neutral-900 dark:text-neutral-100">
    <!-- Modal Header -->
    <div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0 bg-neutral-50/50 dark:bg-neutral-900">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900/60 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
          <Users class="w-4 h-4" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-bold text-neutral-900 dark:text-neutral-100">
              Team Resource Allocation
            </h2>
            <span class="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 text-[10px] font-semibold border border-blue-200 dark:border-blue-900/60">
              {teamRecord.teamName}
            </span>
          </div>
          <p class="text-xs text-neutral-500 dark:text-neutral-400">
            Team Leader: <span class="text-neutral-700 dark:text-neutral-300 font-medium">{teamRecord.teamLeader.name}</span> · Managed by Team Leader
          </p>
        </div>
      </div>
      <button
        type="button"
        onclick={onClose}
        class="p-1 rounded-md text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
      >
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Content Body -->
    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <!-- Permission Notice -->
      {#if !canManage}
        <div class="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 rounded-lg flex items-center gap-3 text-xs text-amber-800 dark:text-amber-300">
          <ShieldAlert class="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <span>
            Read-only mode. Only designated Team Leaders, Admins, or Workspace Owners can modify resource quotas for this team.
          </span>
        </div>
      {/if}

      <!-- Quota Summary Header Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <!-- Total Budget From Admin -->
        <div class="p-3.5 bg-neutral-50 dark:bg-neutral-800/60 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <div class="text-[11px] font-semibold uppercase text-neutral-500 dark:text-neutral-400">
            Admin Allocated Quota
          </div>
          <div class="text-xl font-bold font-mono text-neutral-900 dark:text-neutral-100 mt-1">
            {totalTeamCapGb} <span class="text-xs text-neutral-500 dark:text-neutral-400 font-sans">GB</span>
          </div>
          <div class="text-[11px] text-neutral-400 dark:text-neutral-500 mt-1">
            Global pool granted by IT admin
          </div>
        </div>

        <!-- Distributed to Collections -->
        <div class="p-3.5 rounded-lg border {isOverAllocated ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-900/50' : 'bg-neutral-50 dark:bg-neutral-800/60 border-neutral-200 dark:border-neutral-700'}">
          <div class="text-[11px] font-semibold uppercase text-neutral-500 dark:text-neutral-400">
            Assigned to Collections
          </div>
          <div class="text-xl font-bold font-mono mt-1 {isOverAllocated ? 'text-rose-600 dark:text-rose-400' : 'text-neutral-900 dark:text-neutral-100'}">
            {currentTotalAllocatedGb} <span class="text-xs text-neutral-500 dark:text-neutral-400 font-sans">GB</span>
          </div>
          <div class="text-[11px] text-neutral-400 dark:text-neutral-500 mt-1">
            {allocations.length} collection allocation target(s)
          </div>
        </div>

        <!-- Buffer Reserve -->
        <div class="p-3.5 rounded-lg border {isOverAllocated ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-900/50' : 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-900/50'}">
          <div class="text-[11px] font-semibold uppercase text-neutral-500 dark:text-neutral-400">
            Unallocated Team Buffer
          </div>
          <div class="text-xl font-bold font-mono mt-1 {isOverAllocated ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-700 dark:text-emerald-400'}">
            {unallocatedBufferGb} <span class="text-xs text-neutral-500 dark:text-neutral-400 font-sans">GB</span>
          </div>
          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">
            {isOverAllocated ? 'Over-allocated quota!' : 'Available for new projects'}
          </div>
        </div>
      </div>

      <!-- Allocation Progress Bar -->
      <div class="space-y-1.5">
        <div class="flex justify-between items-center text-xs">
          <span class="font-medium text-neutral-700 dark:text-neutral-300">Team Quota Utilization &amp; Distribution</span>
          <span class="font-mono text-neutral-500 dark:text-neutral-400">
            {currentTotalAllocatedGb} / {totalTeamCapGb} GB ({Math.round((currentTotalAllocatedGb / Math.max(1, totalTeamCapGb)) * 100)}%)
          </span>
        </div>
        <div class="w-full h-2.5 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden flex border border-neutral-200 dark:border-neutral-700">
          <div
            class="h-full transition-all duration-300 {isOverAllocated ? 'bg-rose-500' : 'bg-blue-600'}"
            style="width: {Math.min(100, (currentTotalAllocatedGb / Math.max(1, totalTeamCapGb)) * 100)}%"
          ></div>
        </div>
        {#if isOverAllocated}
          <div class="flex items-center gap-1.5 text-xs text-rose-600 dark:text-rose-400 mt-1 font-medium">
            <AlertTriangle class="w-3.5 h-3.5 shrink-0" />
            <span>Total collection allocations exceed team quota by {Math.abs(unallocatedBufferGb)} GB. Please rebalance before saving.</span>
          </div>
        {/if}
      </div>

      <!-- Collection Distribution List -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-xs font-bold uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
            Collection Quota Distribution
          </h3>
          {#if canManage}
            <button
              type="button"
              onclick={() => (showAddCustom = !showAddCustom)}
              class="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium cursor-pointer"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>Reserve Collection Quota</span>
            </button>
          {/if}
        </div>

        <!-- Optional Custom Target Creator -->
        {#if showAddCustom}
          <div class="p-3 bg-blue-50/60 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/50 rounded-lg space-y-3 animate-in fade-in duration-150">
            <div class="text-xs font-semibold text-blue-900 dark:text-blue-200">Reserve New Collection or Project Quota</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <input
                type="text"
                placeholder="e.g. Microservices &amp; gRPC Docs"
                bind:value={newColName}
                class="sm:col-span-2 px-3 py-1.5 text-xs border border-neutral-300 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-1 focus:ring-blue-600"
              />
              <div class="flex items-center gap-1.5">
                <input
                  type="number"
                  min="1"
                  max={totalTeamCapGb}
                  bind:value={newColGb}
                  class="w-20 px-2 py-1.5 text-xs font-mono border border-neutral-300 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-right focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
                <span class="text-xs text-neutral-500 dark:text-neutral-400 font-mono">GB</span>
                <button
                  type="button"
                  onclick={handleAddCustomAllocation}
                  class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-xs transition-colors cursor-pointer ml-auto"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        {/if}

        <!-- List of Collections and their allocated GB -->
        <div class="border border-neutral-200 dark:border-neutral-800 rounded-lg divide-y divide-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-hidden shadow-2xs">
          {#each allocations as alloc (alloc.collectionId)}
            {@const targetCol = collections.find((c) => c.id === alloc.collectionId)}
            {@const colUsed = targetCol ? getCollectionUsedBytes(targetCol.id, documents) : 0}

            <div class="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-neutral-50/50 dark:hover:bg-neutral-800/40 transition-colors">
              <div class="space-y-0.5 min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <Layers class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                  <span class="text-xs font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                    {alloc.collectionName}
                  </span>
                </div>
                <div class="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
                  <span>Used: <strong class="font-mono text-neutral-700 dark:text-neutral-300">{formatBytes(colUsed)}</strong></span>
                  <span>·</span>
                  <span>{targetCol?.documentCount || 0} docs</span>
                </div>
              </div>

              <!-- Controls -->
              <div class="flex items-center gap-3 shrink-0">
                <!-- Quick preset buttons -->
                {#if canManage}
                  <div class="hidden sm:flex items-center gap-1">
                    {#each [15, 25, 40, 50] as presetVal (presetVal)}
                      <button
                        type="button"
                        onclick={() => handleAllocationChange(alloc.collectionId, presetVal)}
                        class="px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors cursor-pointer {alloc.allocatedGb === presetVal
                          ? 'bg-blue-600 text-white border-blue-600 font-semibold'
                          : 'bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-700'}"
                      >
                        {presetVal}G
                      </button>
                    {/each}
                  </div>
                {/if}

                <!-- Number Input -->
                <div class="flex items-center gap-1.5">
                  <input
                    type="number"
                    min="0"
                    max={totalTeamCapGb}
                    disabled={!canManage}
                    value={alloc.allocatedGb}
                    oninput={(e) => handleAllocationChange(alloc.collectionId, Number((e.currentTarget as HTMLInputElement).value) || 0)}
                    class="w-16 px-2 py-1 text-right font-mono text-xs border border-neutral-300 dark:border-neutral-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:bg-neutral-100 dark:disabled:bg-neutral-800 disabled:text-neutral-400 dark:disabled:text-neutral-500 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100"
                  />
                  <span class="text-xs font-mono text-neutral-500 dark:text-neutral-400 font-medium">GB</span>
                </div>

                {#if canManage && allocations.length > 1}
                  <button
                    type="button"
                    onclick={() => handleRemoveAllocation(alloc.collectionId)}
                    title="Remove allocation target"
                    class="p-1 text-neutral-400 dark:text-neutral-500 hover:text-rose-600 dark:hover:text-rose-400 rounded transition-colors cursor-pointer"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Operational Guidance -->
      <div class="p-3 bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200 dark:border-neutral-700 rounded-lg flex items-start gap-2.5 text-xs text-neutral-600 dark:text-neutral-300">
        <Info class="w-4 h-4 text-neutral-500 dark:text-neutral-400 shrink-0 mt-0.5" />
        <div class="leading-relaxed">
          <strong>Team Leader Authority:</strong> As the team leader of <em>{teamRecord.teamName}</em>, you have autonomous control over how your team's {totalTeamCapGb} GB allocation is shared across internal research, architecture runbooks, and compliance archives. If your team requires more capacity, contact the Workspace IT Admin to increase the base team quota.
        </div>
      </div>
    </div>

    <!-- Modal Footer -->
    <div class="px-6 py-3.5 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900 flex items-center justify-between shrink-0">
      <div class="text-xs text-neutral-500 dark:text-neutral-400">
        {#if saveSuccess}
          <span class="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
            <CheckCircle2 class="w-4 h-4" />
            Team allocations updated successfully!
          </span>
        {:else}
          <span>Unallocated Buffer: <strong class="font-mono text-neutral-700 dark:text-neutral-300">{unallocatedBufferGb} GB</strong></span>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={onClose}
          class="px-3 py-1.5 border border-neutral-300 dark:border-neutral-700 rounded-md text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="button"
          onclick={handleSave}
          disabled={!canManage || isOverAllocated}
          class="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <span>Save Team Allocations</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </div>
</div>
