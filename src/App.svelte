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
    UserProfile,
    ChatThread
  } from './types';
  import {
    CURRENT_USER,
    DEFAULT_RESOURCE_ALLOCATION,
    INITIAL_COLLECTIONS,
    INITIAL_DOCUMENTS,
    INITIAL_TEAM_ALLOCATIONS,
    PRESET_USERS
  } from './data/mockData';
  import { INITIAL_CHAT_THREADS } from './data/chatAndEvalData';
  import { DEFAULT_INGESTION_CONFIG, reindexDocument, chunkTextIntoPages } from './utils/chunker';
  import { checkCollectionQuota } from './utils/resourceUtils';
  import {
    canAccessAdmin,
    canCreateCollection,
    canCreateCollectionInScope,
    canUploadToCollection,
    canDeleteDocument,
    canDeleteCollection
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
  import DeleteDocumentModal from './components/DeleteDocumentModal.svelte';
  import DeleteCollectionModal from './components/DeleteCollectionModal.svelte';
  import VectorGraphView from './components/VectorGraphView.svelte';
  import ChatView from './components/ChatView.svelte';
  import EvaluationView from './components/EvaluationView.svelte';
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
  let activeView = $state<'home' | 'collections' | 'search' | 'admin' | 'graph' | 'chat' | 'eval'>('home');
  let selectedScope = $state<ScopeType>('all');
  let selectedCollectionId = $state<string | null>(null);
  let selectedGraphCollectionId = $state<string>('all');

  // Chat State
  let chatThreads = $state<ChatThread[]>(INITIAL_CHAT_THREADS);
  let activeThreadId = $state<string>(INITIAL_CHAT_THREADS[0]?.id || '');

  function handleSelectThread(threadId: string) {
    activeThreadId = threadId;
    activeView = 'chat';
    selectedCollectionId = null;
  }

  function handleNewChat() {
    const newId = `thread-${Date.now()}`;
    const newThread: ChatThread = {
      id: newId,
      title: 'New Conversation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      collectionId: 'all',
      messages: []
    };
    chatThreads = [newThread, ...chatThreads];
    activeThreadId = newId;
    activeView = 'chat';
    selectedCollectionId = null;
  }

  function handleOpenGraph(collectionId?: string) {
    if (collectionId) {
      selectedGraphCollectionId = collectionId;
    }
    selectedCollectionId = null;
    activeView = 'graph';
  }

  // User State with RBAC role
  let currentUser = $state<UserProfile>(CURRENT_USER);

  // Admin Ingestion & Governance Settings State
  let ingestionConfig = $state<IngestionConfig>(DEFAULT_INGESTION_CONFIG);
  let reindexHistory = $state<ReindexJob[]>(INITIAL_REINDEX_JOBS);

  // Storage Resource Allocations (GB Quotas)
  let scopeResourceAllocation = $state<ScopeResourceAllocation>(DEFAULT_RESOURCE_ALLOCATION);
  let teamAllocations = $state<TeamAllocationRecord[]>(INITIAL_TEAM_ALLOCATIONS);
  let activeTeamModalRecord = $state<TeamAllocationRecord | null>(null);
  let documentToDelete = $state<DocumentItem | null>(null);
  let isDeleteDocModalOpen = $state(false);
  let collectionToDelete = $state<Collection | null>(null);
  let isDeleteColModalOpen = $state(false);

  import { onMount } from 'svelte';

  // Data State
  let collections = $state<Collection[]>(INITIAL_COLLECTIONS);
  let documents = $state<DocumentItem[]>(INITIAL_DOCUMENTS);

  async function loadLiveMilvusData() {
    try {
      const [colRes, docRes] = await Promise.all([
        fetch('http://localhost:8080/api/collections'),
        fetch('http://localhost:8080/api/documents')
      ]);
      if (colRes.ok && docRes.ok) {
        const colData = await colRes.json();
        const docData = await docRes.json();
        const cols = Array.isArray(colData) ? colData : (colData.collections || []);
        const docs = Array.isArray(docData) ? docData : (docData.documents || []);
        if (cols.length > 0) {
          collections = cols;
        }
        if (docs.length > 0) {
          documents = docs;
        }
      }
    } catch (e) {
      console.warn('Milvus backend not reachable, using cached knowledge state:', e);
    }
  }

  onMount(() => {
    loadLiveMilvusData();
  });

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

    documentToDelete = docToDelete;
    isDeleteDocModalOpen = true;
  }

  async function executeDeleteDocument(docId: string, purgeVectors: boolean) {
    const docToDelete = documents.find((d) => d.id === docId);
    if (!docToDelete) return;
    const parentCol = collections.find((c) => c.id === docToDelete.collectionId);
    const colId = docToDelete.collectionId;

    try {
      const res = await fetch(`http://localhost:8080/api/collections/${colId}/documents/${docId}?purge_vectors=${purgeVectors}`, {
        method: 'DELETE'
      });
      const data = await res.json();

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

      if (data.has_other_references) {
        showToast(`Document "${docToDelete.title}" removed from ${parentCol?.name || 'collection'}. Kept in other collections.`);
      } else if (data.purged_vectors) {
        showToast(`Document "${docToDelete.title}" removed and ${data.deleted_vectors_count || docToDelete.chunkCount} vectors purged from Milvus.`);
      } else {
        showToast(`Document "${docToDelete.title}" removed from ${parentCol?.name || 'collection'}. Vectors preserved in Milvus.`);
      }

      // Sync live backend data
      loadLiveMilvusData();
    } catch (err) {
      console.warn('Backend document delete warning:', err);
      documents = documents.filter((d) => d.id !== docId);
      showToast(`Document removed from collection.`);
    }
  }

  function handleRequestDeleteCollection(col: Collection) {
    if (!canDeleteCollection(currentUser, col)) {
      showToast(`Permission denied: Your role (${currentUser.systemRole.toUpperCase()}) cannot delete collection "${col.name}".`);
      return;
    }
    collectionToDelete = col;
    isDeleteColModalOpen = true;
  }

  async function executeDeleteCollection(purgeVectors: boolean) {
    if (!collectionToDelete) return;
    const colId = collectionToDelete.id;
    const colName = collectionToDelete.name;

    try {
      const res = await fetch(`http://localhost:8080/api/collections/${colId}?purge_vectors=${purgeVectors}`, {
        method: 'DELETE'
      });
      const data = await res.json();

      collections = collections.filter((c) => c.id !== colId);
      if (selectedCollectionId === colId) {
        selectedCollectionId = null;
      }

      if (data.purged_vectors) {
        showToast(`Collection "${colName}" deleted and associated vectors purged from Milvus.`);
      } else {
        showToast(`Collection "${colName}" removed. Documents preserved in Global Knowledge Base.`);
      }

      loadLiveMilvusData();
    } catch (err) {
      console.warn('Backend collection delete warning:', err);
      collections = collections.filter((c) => c.id !== colId);
      if (selectedCollectionId === colId) {
        selectedCollectionId = null;
      }
      showToast(`Collection "${colName}" deleted.`);
    } finally {
      isDeleteColModalOpen = false;
      collectionToDelete = null;
    }
  }

  function handleRetryFailedDocument(docId: string) {
    const targetDoc = documents.find((d) => d.id === docId);
    if (!targetDoc) return;

    const retryPages = [
      {
        pageNumber: 1,
        header: '1. Scanned Audit Records & Legacy Host Inventory',
        content: `### 1. Scanned Audit Records & Legacy Host Inventory
High-resolution OCR recovery completed. This document contains inventory manifests for retired on-premises data center hardware racks.
All hosts have been decommissioned and disk drives sanitized per NIST 800-88 standards.

### 1.2 Cryptographic Disposal Attestation
Physical destruction certificates have been cryptographically verified and recorded in the audit ledger.`
      },
      {
        pageNumber: 2,
        header: '2. Decommissioning Verification & Sign-Off',
        content: `### 2. Decommissioning Verification & Sign-Off
Signed off by Chief Information Security Officer and External Auditors.
Hardware serial numbers matched against asset registry with 100% concordance.`
      }
    ];

    const pages = chunkTextIntoPages(targetDoc.id, targetDoc.collectionId, 'org', retryPages, ingestionConfig);
    const totalChunks = pages.reduce((acc, p) => acc + p.chunks.length, 0);

    documents = documents.map((doc) => {
      if (doc.id === docId) {
        return {
          ...doc,
          status: 'indexed' as const,
          errorMessage: undefined,
          chunkCount: totalChunks,
          pageCount: pages.length,
          pages,
        };
      }
      return doc;
    });

    // Also update collection document count & chunks count
    collections = collections.map((col) => {
      if (col.id === targetDoc.collectionId) {
        return {
          ...col,
          totalChunks: col.totalChunks + totalChunks,
          updatedAt: new Date().toISOString(),
        };
      }
      return col;
    });

    const recoveryJob: ReindexJob = {
      id: `job-retry-${Date.now()}`,
      timestamp: new Date().toISOString(),
      targetScope: targetDoc.collectionId,
      targetName: targetDoc.title,
      triggeredBy: `${currentUser.name} (${currentUser.systemRole})`,
      chunkSizeTokens: ingestionConfig.maxChunkSizeTokens,
      chunkOverlapTokens: ingestionConfig.chunkOverlapTokens,
      strategy: ingestionConfig.chunkingStrategy,
      docsCount: 1,
      chunksBefore: 0,
      chunksAfter: totalChunks,
      durationMs: 420,
      status: 'completed',
    };
    reindexHistory = [recoveryJob, ...reindexHistory];

    showToast(`Document "${targetDoc.title}" successfully re-extracted and ${totalChunks} vector chunks indexed.`);
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
    threads={chatThreads}
    {activeThreadId}
    onSelectThread={handleSelectThread}
    onNewChat={handleNewChat}
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
        {reindexHistory}
        {scopeResourceAllocation}
        {ingestionConfig}
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
        onOpenUploadModal={() => {
          if (!selectedCollectionId && collections.length > 0) {
            selectedCollectionId = collections[0].id;
          }
          isUploadModalOpen = true;
        }}
        onOpenDriveModal={() => {
          if (!selectedCollectionId && collections.length > 0) {
            selectedCollectionId = collections[0].id;
          }
          isDriveModalOpen = true;
        }}
        onRetryFailedDocument={handleRetryFailedDocument}
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
    {:else if activeView === 'graph'}
      <VectorGraphView
        {currentUser}
        {collections}
        {documents}
        initialCollectionId={selectedGraphCollectionId}
        onOpenDocument={handleOpenDocument}
      />
    {:else if activeView === 'chat'}
      <ChatView
        {currentUser}
        {collections}
        {documents}
        bind:threads={chatThreads}
        bind:activeThreadId
        onSelectThread={handleSelectThread}
        onNewThread={handleNewChat}
        onOpenDocument={handleOpenDocument}
      />
    {:else if activeView === 'eval'}
      <EvaluationView
        {collections}
        {documents}
      />
    {:else if selectedCollection}
      <CollectionDetailView
        collection={selectedCollection}
        {collections}
        {documents}
        {currentUser}
        {teamAllocations}
        onOpenTeamAllocationModal={(team) => (activeTeamModalRecord = team)}
        onBack={() => (selectedCollectionId = null)}
        onOpenGraph={() => handleOpenGraph(selectedCollection?.id)}
        onOpenUploadModal={() => (isUploadModalOpen = true)}
        onOpenDriveModal={() => (isDriveModalOpen = true)}
        onOpenDocument={handleOpenDocument}
        onDeleteDocument={handleDeleteDocument}
        onDeleteCollection={handleRequestDeleteCollection}
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
        onDeleteCollection={handleRequestDeleteCollection}
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

  <!-- 6. Delete Document & Vector Warning Modal -->
  {#if isDeleteDocModalOpen && documentToDelete}
    {@const targetCol = collections.find((c) => c.id === documentToDelete?.collectionId)}
    <DeleteDocumentModal
      document={documentToDelete}
      collection={targetCol}
      onClose={() => {
        isDeleteDocModalOpen = false;
        documentToDelete = null;
      }}
      onConfirmDelete={async (purgeVectors) => {
        if (documentToDelete) {
          await executeDeleteDocument(documentToDelete.id, purgeVectors);
        }
        isDeleteDocModalOpen = false;
        documentToDelete = null;
      }}
    />
  {/if}

  <!-- 7. Delete Collection Modal -->
  {#if isDeleteColModalOpen && collectionToDelete}
    {@const colDocs = documents.filter((d) => d.collectionId === collectionToDelete?.id)}
    {@const docCount = colDocs.length}
    {@const chunkCount = collectionToDelete.totalChunks || colDocs.reduce((acc, d) => acc + (d.chunkCount || 0), 0)}
    <DeleteCollectionModal
      collection={collectionToDelete}
      documentCount={docCount}
      totalChunks={chunkCount}
      onClose={() => {
        isDeleteColModalOpen = false;
        collectionToDelete = null;
      }}
      onConfirmDelete={async (purgeVectors) => {
        await executeDeleteCollection(purgeVectors);
      }}
    />
  {/if}
</div>
