<script lang="ts">
  import type {
    Collection,
    DocumentItem,
    IngestionConfig,
    ReindexJob,
    ScopeResourceAllocation,
    ScopeType,
    SystemRole,
    TeamAllocationRecord,
    UserProfile
  } from './types';
  import {
    CURRENT_USER,
    DEFAULT_RESOURCE_ALLOCATION,
    INITIAL_COLLECTIONS,
    INITIAL_DOCUMENTS,
    INITIAL_TEAM_ALLOCATIONS,
    PRESET_USERS
  } from './data/mockData';
  import { DEFAULT_INGESTION_CONFIG, reindexDocument } from './utils/chunker';
  import { checkCollectionQuota } from './utils/resourceUtils';
  import {
    canAccessAdmin,
    canCreateCollection,
    canCreateCollectionInScope,
    canUploadToCollection,
    canDeleteDocument
  } from './utils/governance';
  import Sidebar from './components/Sidebar.svelte';
  import HomeView from './components/HomeView.svelte';
  import CollectionsView from './components/CollectionsView.svelte';
  import CollectionDetailView from './components/CollectionDetailView.svelte';
  import SearchView from './components/SearchView.svelte';
  import AdminView from './components/AdminView.svelte';
  import DocumentViewerModal from './components/DocumentViewerModal.svelte';
  import DrivePickerModal from './components/DrivePickerModal.svelte';
  import UploadModal from './components/UploadModal.svelte';
  import NewCollectionModal from './components/NewCollectionModal.svelte';
  import TeamAllocationModal from './components/TeamAllocationModal.svelte';
  import { CheckCircle2, Menu, Layers, Sun, Moon } from '@lucide/svelte';

  const INITIAL_REINDEX_JOBS: ReindexJob[] = [
    {
      id: 'job-init-1',
      timestamp: '2026-09-23T04:15:00Z',
      targetScope: 'all',
      targetName: 'All Collections (Global)',
      triggeredBy: 'Elena Rostova (owner)',
      chunkSizeTokens: 256,
      chunkOverlapTokens: 32,
      strategy: 'paragraph_boundary',
      docsCount: 12,
      chunksBefore: 68,
      chunksAfter: 76,
      durationMs: 820,
      status: 'completed',
    },
    {
      id: 'job-init-2',
      timestamp: '2026-09-20T11:30:00Z',
      targetScope: 'col-org-1',
      targetName: 'Enterprise Zero Trust & Identity Standards',
      triggeredBy: 'Security Architecture Council (admin)',
      chunkSizeTokens: 180,
      chunkOverlapTokens: 24,
      strategy: 'paragraph_boundary',
      docsCount: 3,
      chunksBefore: 20,
      chunksAfter: 22,
      durationMs: 340,
      status: 'completed',
    }
  ];

  // Navigation State
  let activeView = $state<'home' | 'collections' | 'search' | 'admin'>('home');
  let selectedScope = $state<ScopeType>('all');
  let selectedCollectionId = $state<string | null>(null);

  // User State with RBAC role
  let currentUser = $state<UserProfile>(CURRENT_USER);

  // Admin Ingestion & Governance Settings State
  let ingestionConfig = $state<IngestionConfig>(DEFAULT_INGESTION_CONFIG);
  let reindexHistory = $state<ReindexJob[]>(INITIAL_REINDEX_JOBS);

  // Storage Resource Allocations (GB Quotas)
  let scopeResourceAllocation = $state<ScopeResourceAllocation>(DEFAULT_RESOURCE_ALLOCATION);
  let teamAllocations = $state<TeamAllocationRecord[]>(INITIAL_TEAM_ALLOCATIONS);
  let activeTeamModalRecord = $state<TeamAllocationRecord | null>(null);

  // Data State
  let collections = $state<Collection[]>(INITIAL_COLLECTIONS);
  let documents = $state<DocumentItem[]>(INITIAL_DOCUMENTS);

  // Modal States
  let isNewCollectionOpen = $state(false);
  let isDriveModalOpen = $state(false);
  let isUploadModalOpen = $state(false);
  let isMobileSidebarOpen = $state(false);

  // Dark Mode State
  function getInitialDarkMode(): boolean {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('cognify_dark_mode') ?? localStorage.getItem('nexus_dark_mode');
      if (saved !== null) {
        return saved === 'true';
      }
      return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
    }
    return false;
  }

  let isDarkMode = $state<boolean>(getInitialDarkMode());

  $effect(() => {
    if (typeof document !== 'undefined') {
      if (isDarkMode) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('cognify_dark_mode', 'true');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('cognify_dark_mode', 'false');
      }
    }
  });

  function handleToggleDarkMode() {
    isDarkMode = !isDarkMode;
  }

  // Document Viewer Modal with Deep Link Target State
  let viewingDocState = $state<{
    doc: DocumentItem;
    page?: number;
    chunkId?: string;
  } | null>(null);

  // Toast Notification
  let toastMessage = $state<string | null>(null);
  let toastTimeout: any = null;

  function showToast(msg: string) {
    if (toastTimeout) clearTimeout(toastTimeout);
    toastMessage = msg;
    toastTimeout = setTimeout(() => {
      toastMessage = null;
    }, 3500);
  }

  let selectedCollection = $derived(collections.find((c) => c.id === selectedCollectionId));

  // Governance Route Guard: Ensure unauthorized roles (such as viewer or member) cannot view or stay in Admin
  $effect(() => {
    if (activeView === 'admin' && !canAccessAdmin(currentUser)) {
      activeView = 'collections';
      showToast(`Access restricted: ${currentUser.systemRole.toUpperCase()} accounts cannot access Admin & Resources.`);
    }
  });

  // User Role Switcher with Persona synchronization
  function handleSwitchUserRole(newRole: SystemRole) {
    const preset = PRESET_USERS.find((u) => u.systemRole === newRole);
    if (preset) {
      currentUser = preset;
      showToast(`Switched active user to ${preset.name} (${newRole.toUpperCase()}).`);
    } else {
      currentUser = { ...currentUser, systemRole: newRole };
      showToast(`Switched active user role to "${newRole.toUpperCase()}".`);
    }
    if (activeView === 'admin' && !canAccessAdmin(preset || currentUser)) {
      activeView = 'collections';
    }
  }

  // Team Resource Allocation Handler
  function handleUpdateTeamAllocation(updatedRecord: TeamAllocationRecord) {
    if (currentUser.systemRole !== 'owner' && currentUser.systemRole !== 'admin' && currentUser.systemRole !== 'team_lead') {
      showToast('Permission denied: You do not have permission to modify team quotas.');
      return;
    }

    teamAllocations = teamAllocations.map((t) =>
      t.teamId === updatedRecord.teamId ? updatedRecord : t
    );

    // Sync collection allocatedGb
    collections = collections.map((col) => {
      const matchingAlloc = updatedRecord.collectionAllocations.find((a) => a.collectionId === col.id);
      if (matchingAlloc) {
        return { ...col, allocatedGb: matchingAlloc.allocatedGb };
      }
      return col;
    });

    showToast(`Storage quotas updated for team: ${updatedRecord.teamName}.`);
  }

  // Actions
  function handleCreateCollection(newCol: Collection) {
    if (!canCreateCollection(currentUser) || !canCreateCollectionInScope(currentUser, newCol.scope)) {
      showToast(`Access denied: Your account (${currentUser.systemRole.toUpperCase()}) cannot create ${newCol.scope} collections.`);
      return;
    }
    collections = [newCol, ...collections];
    selectedCollectionId = newCol.id;
    activeView = 'collections';
    showToast(`Collection "${newCol.name}" created successfully.`);
  }

  function handleDriveImportComplete(newDocs: DocumentItem[]): boolean {
    if (!canUploadToCollection(currentUser, selectedCollection)) {
      showToast(`Permission denied: Your role (${currentUser.systemRole.toUpperCase()}) cannot import documents.`);
      return false;
    }

    if (selectedCollectionId) {
      const targetCol = collections.find((c) => c.id === selectedCollectionId);
      if (targetCol) {
        const totalIncomingBytes = newDocs.reduce((acc, d) => acc + (d.sizeBytes || 0), 0);
        const quotaCheck = checkCollectionQuota(
          targetCol,
          totalIncomingBytes,
          documents,
          scopeResourceAllocation,
          teamAllocations
        );

         if (!quotaCheck.allowed) {
          showToast(`⚠️ Storage Quota Exceeded: ${quotaCheck.reason || 'Operation blocked by quota limits.'}`);
          return false;
        }
      }
    }

    documents = [...newDocs, ...documents];
    if (selectedCollectionId) {
      const addedChunks = newDocs.reduce((acc, d) => acc + d.chunkCount, 0);
      collections = collections.map((c) =>
        c.id === selectedCollectionId
          ? {
              ...c,
              documentCount: c.documentCount + newDocs.length,
              totalChunks: c.totalChunks + addedChunks,
              updatedAt: new Date().toISOString(),
            }
          : c
      );
    }
    showToast(`Ingested ${newDocs.length} document(s) from Drive with ${ingestionConfig.maxChunkSizeTokens}t chunks.`);
    return true;
  }

  function handleUploadComplete(newDoc: DocumentItem): boolean {
    if (!canUploadToCollection(currentUser, selectedCollection)) {
      showToast(`Permission denied: Your role (${currentUser.systemRole.toUpperCase()}) cannot upload documents.`);
      return false;
    }

    if (selectedCollectionId) {
      const targetCol = collections.find((c) => c.id === selectedCollectionId);
      if (targetCol) {
        const quotaCheck = checkCollectionQuota(
          targetCol,
          newDoc.sizeBytes || 0,
          documents,
          scopeResourceAllocation,
          teamAllocations
        );

        if (!quotaCheck.allowed) {
          showToast(`⚠️ Storage Quota Exceeded: ${quotaCheck.reason || 'Upload blocked by storage limits.'}`);
          return false;
        }
      }
    }

    documents = [newDoc, ...documents];
    if (selectedCollectionId) {
      collections = collections.map((c) =>
        c.id === selectedCollectionId
          ? {
              ...c,
              documentCount: c.documentCount + 1,
              totalChunks: c.totalChunks + newDoc.chunkCount,
              updatedAt: new Date().toISOString(),
            }
          : c
      );
    }
    showToast(`Document "${newDoc.title}" extracted and ingested with active token window.`);
    return true;
  }

  function handleDeleteDocument(docId: string) {
    const docToDelete = documents.find((d) => d.id === docId);
    if (!docToDelete) return;

    const parentCol = collections.find((c) => c.id === docToDelete.collectionId);
    if (!canDeleteDocument(currentUser, docToDelete, parentCol)) {
      showToast(`Permission denied: Your role (${currentUser.systemRole.toUpperCase()}) cannot delete this document.`);
      return;
    }

    documents = documents.filter((d) => d.id !== docId);
    collections = collections.map((c) =>
      c.id === docToDelete.collectionId
        ? {
            ...c,
            documentCount: Math.max(0, c.documentCount - 1),
            totalChunks: Math.max(0, c.totalChunks - docToDelete.chunkCount),
            updatedAt: new Date().toISOString(),
          }
        : c
    );
    showToast(`Document removed from collection.`);
  }

  async function handleTriggerReindex(targetScope: 'all' | string): Promise<ReindexJob> {
    const startTime = Date.now();
    const targetDocs =
      targetScope === 'all'
        ? documents
        : documents.filter((d) => d.collectionId === targetScope);

    const targetName =
      targetScope === 'all'
        ? 'All Collections (Global)'
        : collections.find((c) => c.id === targetScope)?.name || 'Specified Collection';

    const chunksBefore = targetDocs.reduce((acc, d) => acc + d.chunkCount, 0);

    // Re-chunk every target document with current ingestionConfig
    const updatedTargetDocs = targetDocs.map((doc) => reindexDocument(doc, ingestionConfig));
    const updatedDocMap = new Map(updatedTargetDocs.map((d) => [d.id, d]));

    const nextDocuments = documents.map((d) => updatedDocMap.get(d.id) || d);
    documents = nextDocuments;

    // Recompute total chunk counts for affected collections
    collections = collections.map((col) => {
      const colDocs = nextDocuments.filter((d) => d.collectionId === col.id);
      const totalChunks = colDocs.reduce((acc, d) => acc + d.chunkCount, 0);
      return {
        ...col,
        documentCount: colDocs.length,
        totalChunks,
        updatedAt: new Date().toISOString(),
      };
    });

    const chunksAfter = updatedTargetDocs.reduce((acc, d) => acc + d.chunkCount, 0);
    const durationMs = Date.now() - startTime + 520;

    const newJob: ReindexJob = {
      id: `job-${Date.now()}`,
      timestamp: new Date().toISOString(),
      targetScope,
      targetName,
      triggeredBy: `${currentUser.name} (${currentUser.systemRole})`,
      chunkSizeTokens: ingestionConfig.maxChunkSizeTokens,
      chunkOverlapTokens: ingestionConfig.chunkOverlapTokens,
      strategy: ingestionConfig.chunkingStrategy,
      docsCount: targetDocs.length,
      chunksBefore,
      chunksAfter,
      durationMs,
      status: 'completed',
    };

    reindexHistory = [newJob, ...reindexHistory];
    showToast(
      `Re-indexed ${targetDocs.length} doc(s): generated ${chunksAfter} chunks (${chunksAfter - chunksBefore >= 0 ? '+' : ''}${chunksAfter - chunksBefore}).`
    );

    return newJob;
  }

  function handleOpenDocument(doc: DocumentItem, pageNumber?: number) {
    viewingDocState = {
      doc,
      page: pageNumber,
    };
  }

  function handleOpenCitation(doc: DocumentItem, pageNumber: number, chunkId: string) {
    viewingDocState = {
      doc,
      page: pageNumber,
      chunkId,
    };
  }

  function openNewCollectionModal() {
    if (!canCreateCollection(currentUser)) {
      showToast(`Access restricted: ${currentUser.systemRole.toUpperCase()} accounts cannot create collections.`);
      return;
    }
    isNewCollectionOpen = true;
  }

  function openAdminView() {
    if (!canAccessAdmin(currentUser)) {
      showToast(`Access restricted: ${currentUser.systemRole.toUpperCase()} accounts cannot access Admin & Resources.`);
      return;
    }
    selectedCollectionId = null;
    activeView = 'admin';
  }
</script>

<div class="flex h-screen w-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 font-sans antialiased transition-colors">
  <!-- Left-Hand Vertical Rail Navigation -->
  <Sidebar
    {activeView}
    onSelectView={(v) => {
      isMobileSidebarOpen = false;
      if (v === 'admin' && !canAccessAdmin(currentUser)) {
        showToast('Access restricted: You do not have permission to view Admin & Resources.');
        return;
      }
      activeView = v;
      if (v !== 'collections') {
        selectedCollectionId = null;
      }
    }}
    {selectedScope}
    onSelectScope={(s) => {
      isMobileSidebarOpen = false;
      selectedScope = s;
      selectedCollectionId = null;
      activeView = 'collections';
    }}
    {selectedCollectionId}
    onSelectCollection={(id) => {
      isMobileSidebarOpen = false;
      selectedCollectionId = id;
      activeView = 'collections';
    }}
    {collections}
    {documents}
    {scopeResourceAllocation}
    onOpenNewCollection={() => {
      isMobileSidebarOpen = false;
      openNewCollectionModal();
    }}
    {currentUser}
    onChangeUserRole={handleSwitchUserRole}
    {isDarkMode}
    onToggleDarkMode={handleToggleDarkMode}
    isMobileOpen={isMobileSidebarOpen}
    onCloseMobile={() => (isMobileSidebarOpen = false)}
  />

  <!-- Main Application Wrapper -->
  <div class="flex-1 flex flex-col min-w-0 overflow-hidden relative h-screen">
    <!-- Mobile Top Navigation Header Bar (Visible on mobile/tablet < md) -->
    <header class="md:hidden h-12 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between px-3 shrink-0 z-30">
      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={() => (isMobileSidebarOpen = true)}
          class="p-1.5 rounded-lg text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          aria-label="Open navigation menu"
          title="Open Menu"
        >
          <Menu class="w-5 h-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white shrink-0 shadow-xs">
            <Layers class="w-3.5 h-3.5 text-white" />
          </div>
          <span class="font-semibold text-sm text-neutral-900 dark:text-neutral-100 tracking-tight">Cognify</span>
        </div>
      </div>

      <div class="flex items-center gap-1">
        <button
          type="button"
          onclick={handleToggleDarkMode}
          class="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          title={isDarkMode ? 'Switch to Light mode' : 'Switch to Dark mode'}
          aria-label="Toggle dark mode"
        >
          {#if isDarkMode}
            <Sun class="w-4 h-4 text-amber-400" />
          {:else}
            <Moon class="w-4 h-4 text-neutral-600 dark:text-neutral-400" />
          {/if}
        </button>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
      {#if activeView === 'home'}
      <HomeView
        {currentUser}
        {collections}
        {documents}
        onSelectCollection={(id) => {
          selectedCollectionId = id;
          activeView = 'collections';
        }}
        onOpenDocument={handleOpenDocument}
        onNavigate={(view) => {
          activeView = view;
          selectedCollectionId = null;
        }}
        onOpenNewCollection={openNewCollectionModal}
      />
    {:else if activeView === 'admin' && canAccessAdmin(currentUser)}
      <AdminView
        {currentUser}
        onChangeUserRole={handleSwitchUserRole}
        {collections}
        {documents}
        {ingestionConfig}
        onUpdateIngestionConfig={(newConfig) => {
          ingestionConfig = newConfig;
          showToast(`Ingestion settings saved: ${newConfig.maxChunkSizeTokens}t / ${newConfig.chunkOverlapTokens}t.`);
        }}
        onTriggerReindex={handleTriggerReindex}
        {reindexHistory}
        {scopeResourceAllocation}
        onUpdateScopeResourceAllocation={(newAlloc) => {
          scopeResourceAllocation = newAlloc;
          showToast("Scope quotas updated successfully.");
        }}
        {teamAllocations}
        onUpdateTeamAllocation={handleUpdateTeamAllocation}
        onOpenTeamAllocationModal={(team) => (activeTeamModalRecord = team)}
      />
    {:else if activeView === 'search'}
      <SearchView
        {documents}
        {collections}
        onOpenCitation={handleOpenCitation}
      />
    {:else if selectedCollection}
      <CollectionDetailView
        collection={selectedCollection}
        {documents}
        {currentUser}
        {teamAllocations}
        onOpenTeamAllocationModal={(team) => (activeTeamModalRecord = team)}
        onBack={() => (selectedCollectionId = null)}
        onOpenUploadModal={() => (isUploadModalOpen = true)}
        onOpenDriveModal={() => (isDriveModalOpen = true)}
        onOpenDocument={handleOpenDocument}
        onDeleteDocument={handleDeleteDocument}
      />
    {:else}
      <CollectionsView
        {collections}
        {selectedScope}
        onSelectScope={(s) => (selectedScope = s)}
        onSelectCollection={(id) => (selectedCollectionId = id)}
        onOpenNewCollection={openNewCollectionModal}
        onOpenAdmin={openAdminView}
        {currentUser}
        {teamAllocations}
        onOpenTeamAllocationModal={(team) => (activeTeamModalRecord = team)}
      />
    {/if}

    <!-- Global Floating Toast -->
    {#if toastMessage}
      <div class="fixed bottom-5 right-5 z-50 bg-neutral-900 text-white text-xs px-3.5 py-2 rounded-lg shadow-lg flex items-center gap-2 border border-neutral-700 animate-in slide-in-from-bottom-2 fade-in duration-200">
        <CheckCircle2 class="w-4 h-4 text-emerald-400 shrink-0" />
        <span>{toastMessage}</span>
      </div>
    {/if}
  </main>
  </div>

  <!-- Modals -->
  <!-- 1. New Collection Modal -->
  {#if isNewCollectionOpen}
    <NewCollectionModal
      {currentUser}
      onClose={() => (isNewCollectionOpen = false)}
      onCreate={handleCreateCollection}
    />
  {/if}

  <!-- 2. Drive Picker Modal (Ingestion) -->
  {#if isDriveModalOpen && selectedCollection}
    <DrivePickerModal
      collection={selectedCollection}
      existingDocTitles={documents
        .filter((d) => d.collectionId === selectedCollection.id)
        .map((d) => d.title)}
      {ingestionConfig}
      onClose={() => (isDriveModalOpen = false)}
      onImportComplete={handleDriveImportComplete}
    />
  {/if}

  <!-- 3. Direct Upload Modal (Ingestion) -->
  {#if isUploadModalOpen && selectedCollection}
    <UploadModal
      collection={selectedCollection}
      {ingestionConfig}
      {currentUser}
      onClose={() => (isUploadModalOpen = false)}
      onUploadComplete={handleUploadComplete}
    />
  {/if}

  <!-- 4. Deep-Linking Document Viewer Modal -->
  {#if viewingDocState}
    <DocumentViewerModal
      document={viewingDocState.doc}
      initialPage={viewingDocState.page}
      initialChunkId={viewingDocState.chunkId}
      onClose={() => (viewingDocState = null)}
    />
  {/if}

  <!-- 5. Team Resource Allocation Modal -->
  {#if activeTeamModalRecord}
    <TeamAllocationModal
      teamRecord={activeTeamModalRecord}
      {collections}
      {documents}
      {currentUser}
      onClose={() => (activeTeamModalRecord = null)}
      onSaveAllocations={(updatedRecord) => {
        handleUpdateTeamAllocation(updatedRecord);
      }}
    />
  {/if}
</div>
