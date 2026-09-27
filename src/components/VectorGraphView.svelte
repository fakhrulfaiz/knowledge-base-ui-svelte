<script lang="ts">
  import {
    Network,
    Search,
    RefreshCw,
    X,
    Filter,
    Layers,
    FileText,
    Database,
    Zap,
    ZoomIn,
    ZoomOut,
    Maximize2,
    Sparkles,
    Copy,
    Check,
    Eye,
    Compass,
    Activity,
    SlidersHorizontal,
    RotateCcw,
    AlertCircle,
    Sun,
    Moon
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, UserProfile } from '../types';

  interface Props {
    currentUser?: UserProfile;
    collections?: Collection[];
    documents?: DocumentItem[];
    initialCollectionId?: string;
    onOpenDocument: (doc: DocumentItem, pageNumber?: number, chunkId?: string) => void;
    onSelectCollection?: (colId: string) => void;
  }

  let {
    currentUser,
    collections = [],
    documents = [],
    initialCollectionId = 'all',
    onOpenDocument,
    onSelectCollection
  }: Props = $props();

  const BACKEND_URL = 'http://localhost:8080';

  function hslToHex(h: number, s: number, l: number): string {
    l /= 100;
    const a = (s * Math.min(l, 1 - l)) / 100;
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color).toString(16).padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
  }

  // Pure dynamic string-to-hex generator:
  // Converts ANY string directly into a vibrant, unique color across the full 360° spectrum
  function getDocColor(identifier: string, isDark: boolean): string {
    if (!identifier) return isDark ? '#38bdf8' : '#0284c7';
    let hash = 0;
    const str = identifier.trim().toLowerCase();
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
      hash |= 0;
    }
    const hue = Math.abs(hash) % 360;
    // 72% saturation for rich vibrance; 58% lightness in dark mode, 44% in light mode for readability
    return hslToHex(hue, 72, isDark ? 58 : 44);
  }

  // Theme State: synchronized with <html> dark class
  let isDarkMode = $state(
    typeof document !== 'undefined'
      ? document.documentElement.classList.contains('dark')
      : true
  );

  function updateNodeColors() {
    if (!nodes || nodes.length === 0) return;
    for (const node of nodes) {
      if (node.is_center) continue;
      const docKey = node.meta?.doc_name || node.doc_name || node.label || node.collection_name || node.meta?.collection_name || 'default';
      node.color = getDocColor(docKey, isDarkMode);
    }
    nodes = [...nodes];
  }

  function toggleTheme() {
    isDarkMode = !isDarkMode;
    if (typeof document !== 'undefined') {
      if (isDarkMode) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('cognify_dark_mode', 'true');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('cognify_dark_mode', 'false');
      }
    }
    updateNodeColors();
  }

  // Observe theme changes made externally (e.g. from sidebar)
  $effect(() => {
    if (typeof MutationObserver !== 'undefined' && typeof document !== 'undefined') {
      const observer = new MutationObserver(() => {
        isDarkMode = document.documentElement.classList.contains('dark');
        updateNodeColors();
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
      return () => observer.disconnect();
    }
  });

  // State
  let searchQuery = $state('');
  let activeSearchQuery = $state('');
  let selectedScope = $state<'all' | 'org' | 'team' | 'project'>('all');
  let selectedCollectionId = $state<string>('all');
  let milvusCollections = $state<any[]>([]);
  let chunksLimit = $state<number>(25);

  let filteredMilvusCollections = $derived(
    milvusCollections.filter((c) => {
      if (selectedScope === 'all') return true;
      if (selectedScope === 'org') return c.scope === 'org';
      if (selectedScope === 'team') return c.scope === 'team';
      if (selectedScope === 'project') return c.scope === 'project';
      return true;
    })
  );

  let hasSearched = $state(false);

  function handleReset() {
    searchQuery = '';
    activeSearchQuery = '';
    hasSearched = false;
    isRadialSearchMode = false;
    nodes = [];
    edges = [];
    selectedNode = null;
    hoveredNode = null;
    hoveredCluster = null;
  }

  function handleScopeChange(newScope: 'all' | 'org' | 'team' | 'project') {
    selectedScope = newScope;
    if (selectedCollectionId !== 'all') {
      const exists = filteredMilvusCollections.some(
        (c) => c.collection_name === selectedCollectionId || c.id === selectedCollectionId
      );
      if (!exists) {
        selectedCollectionId = 'all';
      }
    }
    if (hasSearched && activeSearchQuery) {
      handleSearch();
    }
  }

  $effect(() => {
    if (initialCollectionId) {
      selectedCollectionId = initialCollectionId;
    }
  });

  let isSearching = $state(false);
  let isBackendLive = $state(false);
  let isLoadingGraph = $state(false);
  let errorMessage = $state<string | null>(null);
  let selectedNode = $state<any | null>(null);
  let hoveredNode = $state<any | null>(null);
  let hoveredEdge = $state<any | null>(null);
  let copiedCitation = $state(false);

  // Canvas Viewport & Transform
  let canvasContainer = $state<HTMLDivElement | null>(null);
  let canvasWidth = $state(1000);
  let canvasHeight = $state(650);

  let zoom = $state(1);
  let panX = $state(0);
  let panY = $state(0);
  let isDraggingCanvas = $state(false);
  let dragStartX = $state(0);
  let dragStartY = $state(0);

  // Dragged Node
  let draggedNode = $state<any | null>(null);

  // Graph Data
  let nodes = $state<any[]>([]);
  let edges = $state<any[]>([]);
  let isRadialSearchMode = $state(false);

  // Animation frame loop for fluid spring physics
  let animFrameId: number | null = null;

  // Real suggested queries covering the actual Milvus collections
  const SUGGESTED_QUERIES = [
    '100G optical transceivers',
    'C++ stack frame unwinding',
    'OLAP multidimensional data cube',
    'CORDIS European innovation research',
    'QSFP28 vs CFP4 modules'
  ];

  // Helper: map a doc title / name to local DocumentItem
  function findMatchingDoc(docName: string): DocumentItem | undefined {
    return documents.find(
      (d) =>
        d.title.toLowerCase().includes(docName.toLowerCase()) ||
        docName.toLowerCase().includes(d.title.toLowerCase())
    );
  }

  let hoveredCluster = $state<string | null>(null);

  // Derive semantic cluster distribution from currently displayed nodes
  let clusterStats = $derived.by(() => {
    if (nodes.length <= 1) return [];
    const map = new Map<string, { count: number; color: string; label: string }>();
    for (const n of nodes) {
      if (n.is_center || n.type === 'query') continue;
      const key = n.meta?.doc_name || n.doc_name || n.collection_name || n.meta?.collection_name || 'General';
      const label = n.meta?.doc_name || n.doc_name || n.label || key;
      const item = map.get(key) || { count: 0, color: n.color || getDocColor(key, isDarkMode), label };
      item.count += 1;
      map.set(key, item);
    }
    return Array.from(map.entries()).map(([k, v]) => ({ key: k, ...v }));
  });

  // Check backend health and fetch real Milvus collections
  async function checkBackendHealth() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) {
        const data = await res.json();
        isBackendLive = Boolean(data.connected);
        if (isBackendLive) {
          await fetchMilvusCollections();
        }
      } else {
        isBackendLive = false;
      }
    } catch {
      isBackendLive = false;
    }
  }

  // Fetch real collections directly from Milvus backend
  async function fetchMilvusCollections() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/collections`);
      if (res.ok) {
        const data = await res.json();
        milvusCollections = data.collections || [];
      }
    } catch {
      milvusCollections = [];
    }
  }

  // Load Ambient / Exploratory Graph from Live Milvus
  async function loadGraphData() {
    isLoadingGraph = true;
    errorMessage = null;
    isRadialSearchMode = false;
    activeSearchQuery = '';

    try {
      const targetCol = selectedCollectionId;
      const res = await fetch(
        `${BACKEND_URL}/api/graph?scope=${encodeURIComponent(selectedScope)}&collection_id=${encodeURIComponent(targetCol)}&limit_chunks=${chunksLimit}`
      );
      if (res.ok) {
        const data = await res.json();
        initializeGraphLayout(data.nodes || [], data.edges || [], false);
        isBackendLive = true;
      } else {
        nodes = [];
        edges = [];
        isBackendLive = false;
        errorMessage = 'Unable to reach Milvus backend service.';
      }
    } catch (e: any) {
      nodes = [];
      edges = [];
      isBackendLive = false;
      errorMessage = 'Milvus backend offline (http://localhost:8080).';
    } finally {
      isLoadingGraph = false;
    }
  }

  // Execute Real Cross-Collection Vector Similarity Search on Milvus
  async function handleSearch() {
    const q = searchQuery.trim();
    if (!q) {
      handleReset();
      return;
    }

    isSearching = true;
    errorMessage = null;

    try {
      const res = await fetch(`${BACKEND_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          collection_name: selectedCollectionId,
          scope: selectedScope,
          top_k: chunksLimit
        })
      });

      if (res.ok) {
        const data = await res.json();
        activeSearchQuery = q;
        hasSearched = true;
        isRadialSearchMode = true;
        initializeGraphLayout(data.graph.nodes, data.graph.edges, true);
        selectedNode = null;
      } else {
        const err = await res.json().catch(() => ({}));
        errorMessage = err.detail || 'Milvus vector search returned no results.';
      }
    } catch (e: any) {
      errorMessage = 'Milvus vector search error. Backend offline.';
    } finally {
      isSearching = false;
    }
  }

  // Smooth Physics & Layout Simulation with Genuine Grouping
  // Unified 2D Semantic Vector Space Layout (Attu-Style PCA/SVD for both Default & Search)
  function initializeGraphLayout(rawNodes: any[], rawEdges: any[], radial: boolean) {
    const cx = canvasWidth / 2;
    const cy = canvasHeight / 2;

    const existingCoords = new Map<string, { x: number; y: number }>();
    for (const n of nodes) {
      existingCoords.set(n.id, { x: n.x, y: n.y });
    }

    const layoutScale = Math.min(canvasWidth, canvasHeight) * 0.42;

    for (const node of rawNodes) {
      const docKey = node.meta?.doc_name || node.doc_name || node.label || node.collection_name || 'default';
      if (!node.is_center && node.type !== 'query') {
        node.color = getDocColor(docKey, isDarkMode);
      } else {
        node.color = '#38bdf8';
      }

      // True 2D semantic coordinates directly from Milvus embeddings
      const semX = node.semantic_x ?? 0;
      const semY = node.semantic_y ?? 0;

      const destX = cx + semX * layoutScale;
      const destY = cy + semY * layoutScale;

      const prev = existingCoords.get(node.id);
      node.x = prev ? prev.x : cx + (destX - cx) * 0.3;
      node.y = prev ? prev.y : cy + (destY - cy) * 0.3;
      node.targetX = destX;
      node.targetY = destY;
    }

    // Force-directed collision relaxation to prevent overlapping dots while strictly preserving semantic topology
    const minDistance = 14;
    const iterations = 18;
    for (let iter = 0; iter < iterations; iter++) {
      for (let i = 0; i < rawNodes.length; i++) {
        for (let j = i + 1; j < rawNodes.length; j++) {
          const n1 = rawNodes[i];
          const n2 = rawNodes[j];
          const isSpecial1 = n1.is_center || n1.type === 'query' || n1.type === 'document';
          const isSpecial2 = n2.is_center || n2.type === 'query' || n2.type === 'document';
          const reqDist = (isSpecial1 || isSpecial2) ? 22 : minDistance;

          const dx = n2.targetX - n1.targetX;
          const dy = n2.targetY - n1.targetY;
          const dist = Math.hypot(dx, dy);
          if (dist < reqDist && dist > 0.0001) {
            const overlap = (reqDist - dist) / 2;
            const angle = Math.atan2(dy, dx);
            n1.targetX -= Math.cos(angle) * overlap;
            n1.targetY -= Math.sin(angle) * overlap;
            n2.targetX += Math.cos(angle) * overlap;
            n2.targetY += Math.sin(angle) * overlap;
          }
        }
      }
    }

    nodes = [...rawNodes];
    edges = [...rawEdges];
  }

  // Animation frame loop for butter-smooth gliding movement
  function startPhysicsLoop() {
    function tick() {
      let hasMotion = false;
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        if (node === draggedNode) continue;

        const targetX = node.targetX ?? node.x;
        const targetY = node.targetY ?? node.y;
        const dx = targetX - node.x;
        const dy = targetY - node.y;

        if (Math.abs(dx) > 0.08 || Math.abs(dy) > 0.08) {
          node.x += dx * 0.12;
          node.y += dy * 0.12;
          hasMotion = true;
        } else {
          node.x = targetX;
          node.y = targetY;
        }
      }

      if (hasMotion || draggedNode) {
        nodes = [...nodes];
      }

      animFrameId = requestAnimationFrame(tick);
    }

    if (!animFrameId) {
      animFrameId = requestAnimationFrame(tick);
    }
  }

  function resetViewport() {
    zoom = 1;
    panX = 0;
    panY = 0;
  }

  function getNodeRadius(node: any, isSelected: boolean, isHovered: boolean): number {
    let r = 5.0;
    if (node.is_center || node.type === 'query') r = 10;
    else if (node.type === 'document' || node.type === 'collection') r = 10.5;
    else if (node.score) r = 4.5 + node.score * 2.5;

    if (isSelected) return r + 2.5;
    if (isHovered) return r + 1.5;
    return r;
  }

  // Canvas Mouse Controls with Accurate Bounding Box
  let mouseDownClientX = 0;
  let mouseDownClientY = 0;
  let hasDraggedCanvas = false;

  function onMouseDownCanvas(e: MouseEvent) {
    mouseDownClientX = e.clientX;
    mouseDownClientY = e.clientY;
    hasDraggedCanvas = false;

    const target = e.target as HTMLElement;
    if (target.tagName !== 'svg' && target.id !== 'graph-background') return;
    isDraggingCanvas = true;
    dragStartX = e.clientX - panX;
    dragStartY = e.clientY - panY;
  }

  function onMouseMoveCanvas(e: MouseEvent) {
    if (isDraggingCanvas) {
      if (Math.hypot(e.clientX - mouseDownClientX, e.clientY - mouseDownClientY) > 5) {
        hasDraggedCanvas = true;
      }
      panX = e.clientX - dragStartX;
      panY = e.clientY - dragStartY;
    } else if (draggedNode && canvasContainer) {
      const rect = canvasContainer.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const cx = canvasWidth / 2;
      const cy = canvasHeight / 2;

      const worldX = (mouseX - panX - cx * (1 - zoom)) / zoom;
      const worldY = (mouseY - panY - cy * (1 - zoom)) / zoom;

      draggedNode.x = worldX;
      draggedNode.y = worldY;
      draggedNode.targetX = worldX;
      draggedNode.targetY = worldY;
    }
  }

  function onMouseUpCanvas() {
    isDraggingCanvas = false;
    draggedNode = null;
  }

  function onClickCanvas(e: MouseEvent) {
    // Deselect if user clicked background without panning/dragging
    if (!hasDraggedCanvas) {
      selectedNode = null;
      hoveredEdge = null;
    }
    hasDraggedCanvas = false;
  }

  function onWheelCanvas(e: WheelEvent) {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    zoom = Math.max(0.4, Math.min(2.8, zoom * zoomFactor));
  }

  function handleCopyCitation(text: string) {
    navigator.clipboard?.writeText(text);
    copiedCitation = true;
    setTimeout(() => {
      copiedCitation = false;
    }, 2000);
  }

  $effect(() => {
    checkBackendHealth();
    startPhysicsLoop();

    return () => {
      if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
      }
    };
  });
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape') selectedNode = null; }} />

<div class="flex-1 flex flex-col h-screen overflow-hidden {isDarkMode ? 'bg-[#090d16] text-neutral-100' : 'bg-slate-50 text-slate-800'} transition-colors select-none font-sans">
  <!-- ========================================================================= -->
  <!-- TOP TOOLBAR & CONTROLS -->
  <!-- ========================================================================= -->
  <header class="h-14 border-b {isDarkMode ? 'border-neutral-800/80 bg-[#0c1220]/90' : 'border-slate-200 bg-white/90'} backdrop-blur-md px-6 flex items-center justify-between gap-4 shrink-0 z-20 transition-colors">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg {isDarkMode ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-blue-50 text-blue-600 border-blue-200'} flex items-center justify-center border">
        <Network class="w-4 h-4" />
      </div>
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-sm font-semibold {isDarkMode ? 'text-neutral-100' : 'text-slate-900'} tracking-tight">
            Milvus Vector Graph Explorer
          </h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono {isBackendLive ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}">
            <span class="w-1.5 h-1.5 rounded-full {isBackendLive ? 'bg-emerald-500' : 'bg-red-500'}"></span>
            {isBackendLive ? 'Milvus v2.4 Live' : 'Milvus Offline'}
          </span>
        </div>
      </div>
    </div>

    <!-- Scope Filter, Collection Filter, Density, Metrics & Theme Controls -->
    <div class="flex items-center gap-2">
      <!-- 1. Scope Selector -->
      <div class="flex items-center gap-1.5 {isDarkMode ? 'bg-[#121929] border-neutral-800 text-neutral-200' : 'bg-white border-slate-200 text-slate-700 shadow-2xs'} px-2.5 py-1.5 rounded-lg border text-xs">
        <Layers class="w-3.5 h-3.5 text-blue-500" />
        <select
          bind:value={selectedScope}
          onchange={() => handleScopeChange(selectedScope)}
          class="bg-transparent outline-none cursor-pointer pr-1 text-xs font-medium"
        >
          <option value="all">All Scopes</option>
          <option value="org">Organization</option>
          <option value="team">Team Knowledge</option>
          <option value="project">Project Knowledge</option>
        </select>
      </div>

      <!-- 2. Collection Selector (Filtered by Scope & populated from Milvus) -->
      <div class="flex items-center gap-1.5 {isDarkMode ? 'bg-[#121929] border-neutral-800 text-neutral-200' : 'bg-white border-slate-200 text-slate-700 shadow-2xs'} px-2.5 py-1.5 rounded-lg border text-xs">
        <Filter class="w-3.5 h-3.5 text-purple-500" />
        <select
          bind:value={selectedCollectionId}
          onchange={() => {
            if (hasSearched && activeSearchQuery) {
              handleSearch();
            }
          }}
          class="bg-transparent outline-none cursor-pointer pr-1 text-xs max-w-44 truncate"
        >
          <option value="all">
            {selectedScope === 'all' ? 'All Collections' : `${selectedScope.toUpperCase()} Collections`} ({filteredMilvusCollections.length})
          </option>
          {#each filteredMilvusCollections as col}
            <option value={col.id || col.collection_name}>
              {col.display_name || col.name} ({col.chunk_count || col.totalChunks || 0} vecs)
            </option>
          {/each}
        </select>
      </div>

      <!-- 3. Chunks Limit / Density Selector -->
      <div class="hidden lg:flex items-center gap-1 {isDarkMode ? 'bg-[#121929] border-neutral-800 text-neutral-400' : 'bg-white border-slate-200 text-slate-600 shadow-2xs'} px-2 py-1 rounded-lg border text-xs font-mono">
        <span class="text-[10px] uppercase font-semibold text-neutral-400">Chunks:</span>
        {#each [
          { label: '25', val: 25 },
          { label: '50', val: 50 },
          { label: '100', val: 100 },
          { label: 'All', val: 0 }
        ] as opt}
          <button
            type="button"
            onclick={() => {
              chunksLimit = opt.val;
              if (hasSearched && activeSearchQuery) {
                handleSearch();
              }
            }}
            class="px-2 py-0.5 rounded text-[11px] cursor-pointer transition-colors {chunksLimit === opt.val ? 'bg-blue-600 text-white font-bold shadow-2xs' : 'hover:text-blue-500'}"
            title={opt.val === 0 ? 'Load ALL chunks from Milvus without limits' : `Load up to ${opt.val} chunks per document`}
          >
            {opt.label}
          </button>
        {/each}
      </div>

      <!-- Quick Metrics Counter -->
      <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg {isDarkMode ? 'bg-[#121929] border-neutral-800 text-neutral-400' : 'bg-white border-slate-200 text-slate-600 shadow-2xs'} border text-xs font-mono">
        <span>{nodes.filter(n => !n.is_center && n.type !== 'query').length} vectors</span>
        <span class="opacity-50">•</span>
        <span>{edges.length} edges</span>
      </div>

      <!-- Light / Dark Mode Toggle Button -->
      <button
        type="button"
        onclick={toggleTheme}
        class="p-2 rounded-lg border {isDarkMode ? 'bg-[#121929] border-neutral-800 text-amber-400 hover:text-amber-300 hover:bg-[#1a253e]' : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100 shadow-2xs'} transition-colors cursor-pointer"
        title={isDarkMode ? 'Switch to Light mode' : 'Switch to Dark mode'}
        aria-label="Toggle light/dark mode"
      >
        {#if isDarkMode}
          <Sun class="w-4 h-4 text-amber-400" />
        {:else}
          <Moon class="w-4 h-4 text-slate-600" />
        {/if}
      </button>
    </div>
  </header>

  <!-- ========================================================================= -->
  <!-- EXPANDED ENTERPRISE VECTOR SEARCH BAR (Multi-Collection Ranking) -->
  <!-- ========================================================================= -->
  <div class="px-6 py-4 {isDarkMode ? 'bg-[#0a0f1c] border-neutral-800/80' : 'bg-white border-slate-200'} border-b z-10 shrink-0 transition-colors">
    <div class="max-w-4xl mx-auto space-y-2.5">
      <!-- Search Input Form -->
      <form
        onsubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        class="relative flex items-center shadow-lg {isDarkMode ? 'shadow-black/20' : 'shadow-slate-200/50'}"
      >
        <div class="relative flex-1 flex items-center">
          <Search class="w-5 h-5 {isDarkMode ? 'text-blue-400/80' : 'text-blue-600'} absolute left-4 pointer-events-none" />
          <input
            type="text"
            bind:value={searchQuery}
            placeholder="Search semantically across Milvus (e.g. '100G optical transceivers', 'C++ stack unwinding', 'OLAP data cube')..."
            class="w-full {isDarkMode ? 'bg-[#111827] border-neutral-700/80 text-neutral-100 placeholder-neutral-500 focus:border-blue-500/80' : 'bg-slate-50/80 border-slate-300 text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:bg-white'} border hover:border-blue-400/60 focus:ring-4 focus:ring-blue-500/10 rounded-xl pl-12 pr-36 py-3.5 text-sm outline-none transition-all"
          />
          {#if searchQuery}
            <button
              type="button"
              onclick={handleReset}
              class="absolute right-32 {isDarkMode ? 'text-neutral-400 hover:text-neutral-200' : 'text-slate-400 hover:text-slate-600'} p-1 rounded-md"
              title="Clear input"
            >
              <X class="w-4 h-4" />
            </button>
          {/if}
        </div>

        <!-- Big Vector Search Action Button -->
        <button
          type="submit"
          disabled={isSearching}
          class="absolute right-2 top-2 bottom-2 px-4.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-all cursor-pointer"
        >
          {#if isSearching}
            <RefreshCw class="w-3.5 h-3.5 animate-spin" />
            <span>Embedding...</span>
          {:else}
            <Sparkles class="w-3.5 h-3.5 text-blue-200" />
            <span>Search Milvus</span>
          {/if}
        </button>
      </form>

      <!-- Chunks Retrieval Limit & Search Mode Controls -->
      <div class="flex flex-wrap items-center justify-between gap-2.5 text-xs pt-0.5">
        <!-- Chunks Limit Selector (Similar to Search) -->
        <div class="flex items-center gap-2">
          <span class="{isDarkMode ? 'text-neutral-400' : 'text-slate-500'} text-[11px] font-mono uppercase font-semibold">
            Chunks Limit:
          </span>
          <div class="flex items-center p-0.5 rounded-lg border {isDarkMode ? 'bg-[#111827] border-neutral-800' : 'bg-slate-100 border-slate-200'}">
            {#each [5, 10, 15, 25, 50] as count}
              <button
                type="button"
                onclick={() => {
                  chunksLimit = count;
                  if (activeSearchQuery) {
                    handleSearch();
                  }
                }}
                class="px-2.5 py-1 rounded-md text-[11px] font-mono transition-all cursor-pointer {chunksLimit === count
                  ? 'bg-blue-600 text-white font-semibold shadow-2xs'
                  : isDarkMode
                    ? 'text-neutral-400 hover:text-neutral-200'
                    : 'text-slate-600 hover:text-slate-900'}"
                title="Retrieve top {count} chunks from Milvus"
              >
                {count}
              </button>
            {/each}
          </div>
        </div>

        <!-- Mode Indicator & Graph Reset -->
        <div class="flex items-center gap-2">
          <div
            class="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-mono {isDarkMode ? 'bg-[#111827] border-neutral-800 text-neutral-300' : 'bg-slate-100 border-slate-200 text-slate-700'}"
            title="Dense vector semantic search: Projects your query into 384-dimensional vector space using BAAI/bge-small-en-v1.5 and computes Cosine Similarity directly against Milvus HNSW vectors."
          >
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            <span class="font-semibold">Dense Semantic Only</span>
            <span class="text-neutral-400 text-[10px] hidden sm:inline">(Cosine Sim)</span>
          </div>

          {#if hasSearched}
            <button
              type="button"
              onclick={handleReset}
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md {isDarkMode ? 'bg-neutral-800 hover:bg-neutral-700 text-neutral-300' : 'bg-slate-200 hover:bg-slate-300 text-slate-700'} text-[11px] font-medium transition-colors cursor-pointer"
            >
              <RotateCcw class="w-3 h-3 text-neutral-400" />
              <span>Reset Graph</span>
            </button>
          {/if}
        </div>
      </div>

      <!-- Presets / Quick Vector Exploration Queries -->
      <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="{isDarkMode ? 'text-neutral-500' : 'text-slate-400'} text-[11px] font-mono mr-1">Suggested Queries:</span>
          {#each SUGGESTED_QUERIES as q}
            <button
              type="button"
              onclick={() => {
                searchQuery = q;
                handleSearch();
              }}
              class="px-2.5 py-1 rounded-md {isDarkMode ? 'bg-[#131b2e] hover:bg-[#1c2742] text-neutral-300 hover:text-blue-300 border-neutral-800' : 'bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-600 border-slate-200'} border text-[11px] transition-colors cursor-pointer"
            >
              {q}
            </button>
          {/each}
        </div>
      </div>

      <!-- Semantic Cluster Breakdown (Visible in Both Default and Search Mode) -->
      {#if clusterStats.length > 0}
        <div class="flex flex-wrap items-center gap-2 pt-1 border-t {isDarkMode ? 'border-neutral-800/60' : 'border-slate-200'}">
          <span class="text-[11px] font-mono {isDarkMode ? 'text-neutral-400' : 'text-slate-500'}">
            {isRadialSearchMode ? `Search Clusters (${nodes.filter(n => !n.is_center).length} hits):` : `Document Clusters (${nodes.filter(n => n.type === 'chunk').length} vectors):`}
          </span>
          {#each clusterStats as cluster}
            <button
              type="button"
              onmouseenter={() => (hoveredCluster = cluster.key)}
              onmouseleave={() => { if (hoveredCluster === cluster.key) hoveredCluster = null; }}
              onclick={() => {
                hoveredCluster = hoveredCluster === cluster.key ? null : cluster.key;
              }}
              class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-mono border transition-all cursor-pointer {hoveredCluster === cluster.key ? 'ring-2 ring-blue-500 scale-105' : ''}"
              style="background-color: {cluster.color}15; border-color: {cluster.color}40; color: {cluster.color};"
              title="Filter / highlight {cluster.label}"
            >
              <span class="w-1.5 h-1.5 rounded-full" style="background-color: {cluster.color};"></span>
              <span class="font-medium truncate max-w-44">{cluster.label}</span>
              <span class="font-bold opacity-80">{cluster.count} {isRadialSearchMode ? 'hits' : 'vecs'}</span>
            </button>
          {/each}
          {#if hoveredCluster}
            <button
              type="button"
              onclick={() => (hoveredCluster = null)}
              class="text-[10px] font-mono text-neutral-400 hover:text-neutral-200 underline cursor-pointer ml-1"
            >
              Reset filter
            </button>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- MAIN GRAPH WORKSPACE (Color-Coded Semantic Constellations) -->
  <!-- ========================================================================= -->
  <div
    bind:this={canvasContainer}
    bind:clientWidth={canvasWidth}
    bind:clientHeight={canvasHeight}
    class="flex-1 flex overflow-hidden relative"
  >
    <!-- SVG Graph Interactive Canvas -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <svg
      id="graph-canvas"
      class="flex-1 w-full h-full cursor-grab active:cursor-grabbing select-none"
      onmousedown={onMouseDownCanvas}
      onmousemove={onMouseMoveCanvas}
      onmouseup={onMouseUpCanvas}
      onwheel={onWheelCanvas}
      onclick={onClickCanvas}
    >
      <!-- Background click/drag capture layer (clean transparent, no grid pattern) -->
      <rect id="graph-background" width="100%" height="100%" fill="transparent" />

      <!-- Transformable Graph Layer -->
      <g transform="translate({panX + (canvasWidth / 2) * (1 - zoom)}, {panY + (canvasHeight / 2) * (1 - zoom)}) scale({zoom})">
        <!-- Lines / Edges: Thinner & Color-Grouped -->
        {#each edges as edge}
          {@const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source}
          {@const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target}
          {@const sourceNode = nodes.find((n) => n.id === sourceId)}
          {@const targetNode = nodes.find((n) => n.id === targetId)}
          {#if sourceNode && targetNode}
            {@const isSelectedEdge = selectedNode && (selectedNode.id === sourceNode.id || selectedNode.id === targetNode.id)}
            {@const isNodeHovered = hoveredNode && (hoveredNode.id === sourceNode.id || hoveredNode.id === targetNode.id)}
            {@const isEdgeDirectlyHovered = hoveredEdge && hoveredEdge.source === sourceId && hoveredEdge.target === targetId}
            {@const isActive = isSelectedEdge || isNodeHovered || isEdgeDirectlyHovered}
            <!-- Use document/cluster color for grouped edges, or violet accent for semantic bridges -->
            {@const isBridge = edge.type === 'bridge'}
            {@const isQueryEdge = edge.type === 'query_match' || (sourceNode.is_center || targetNode.is_center)}
            {@const isChunkSim = edge.type === 'chunk_similarity'}
            {@const isSequential = edge.type === 'sequential'}
            {@const isHierarchy = edge.type === 'hierarchy'}
            {@const edgeColor = isActive
              ? (isDarkMode ? '#38bdf8' : '#0284c7')
              : isBridge
              ? (isDarkMode ? '#818cf8' : '#6366f1')
              : isQueryEdge
              ? (isDarkMode ? '#60a5fa' : '#3b82f6')
              : isChunkSim
              ? (isDarkMode ? '#94a3b8' : '#64748b')
              : isSequential
              ? (isDarkMode ? '#475569' : '#cbd5e1')
              : (isDarkMode ? '#334155' : '#cbd5e1')}
            <!-- Ultra-thin, elegant stroke width and low-contrast opacity -->
            {@const strokeWidth = isActive ? 0.85 : 0.45}
            {@const strokeOpacity = isActive
              ? (isDarkMode ? 0.8 : 0.9)
              : isBridge
              ? 0.35
              : isQueryEdge
              ? 0.28
              : isChunkSim
              ? 0.22
              : isSequential
              ? 0.18
              : isHierarchy
              ? 0.08
              : selectedNode
              ? 0.06
              : (isDarkMode ? 0.14 : 0.18)}
            <!-- Visible rendered edge line -->
            <line
              x1={sourceNode.x}
              y1={sourceNode.y}
              x2={targetNode.x}
              y2={targetNode.y}
              stroke={edgeColor}
              stroke-width={strokeWidth}
              stroke-opacity={strokeOpacity}
              stroke-dasharray={isBridge ? '3 3' : isQueryEdge ? '2 2' : isChunkSim ? '2 2' : isSequential ? '2 3' : isHierarchy ? '1 3' : 'none'}
              class="transition-opacity duration-200 pointer-events-none"
            />
            <!-- Invisible wider hit line for hover detection (no visual clutter, smooth hover only) -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <line
              x1={sourceNode.x}
              y1={sourceNode.y}
              x2={targetNode.x}
              y2={targetNode.y}
              stroke="transparent"
              stroke-width="14"
              class="cursor-pointer"
              onmouseenter={() => (hoveredEdge = { ...edge, sourceNode, targetNode })}
              onmouseleave={() => {
                if (hoveredEdge?.source === sourceId && hoveredEdge?.target === targetId) {
                  hoveredEdge = null;
                }
              }}
            />
          {/if}
        {/each}

        <!-- Minimalist Enterprise Nodes (Clean Dots, Distinct Document Colors) -->
        {#each nodes as node (node.id)}
          {@const isSelected = selectedNode?.id === node.id}
          {@const isHovered = hoveredNode?.id === node.id}
          {@const isCenter = Boolean(node.is_center)}
          {@const docKey = node.meta?.doc_name || node.doc_name || node.collection_name || node.meta?.collection_name || node.label}
          {@const isClusterMatch = !hoveredCluster || docKey === hoveredCluster}
          {@const nodeOpacity = hoveredCluster ? (isClusterMatch ? 1.0 : 0.18) : 1.0}
          {@const baseRadius = getNodeRadius(node, isSelected, isHovered)}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <g
            transform="translate({node.x}, {node.y})"
            class="cursor-pointer group transition-opacity duration-150"
            opacity={nodeOpacity}
            onclick={(e) => {
              e.stopPropagation();
              selectedNode = node;
            }}
            onmouseenter={() => (hoveredNode = node)}
            onmouseleave={() => {
              if (hoveredNode?.id === node.id) hoveredNode = null;
            }}
            onmousedown={(e) => {
              e.stopPropagation();
              draggedNode = node;
            }}
          >
            <!-- Outer Accent Beacon / Selection Ring -->
            {#if isSelected}
              <circle
                r={baseRadius + 4.5}
                fill="none"
                stroke={isDarkMode ? '#38bdf8' : '#0284c7'}
                stroke-width="1.5"
                opacity="0.9"
                class="animate-pulse"
              />
            {:else if isHovered}
              <circle
                r={baseRadius + 3.5}
                fill="none"
                stroke={isDarkMode ? '#ffffff' : '#0f172a'}
                stroke-width="1"
                opacity="0.45"
              />
            {/if}

            <!-- Node Core Dot -->
            <circle
              r={baseRadius}
              fill={node.color || (isDarkMode ? '#1890ff' : '#0284c7')}
              stroke={isSelected
                ? '#ffffff'
                : node.type === 'document' || node.type === 'collection'
                ? (isDarkMode ? '#0f172a' : '#1e293b')
                : isCenter
                ? (isDarkMode ? '#7dd3fc' : '#38bdf8')
                : (isDarkMode ? '#0f172a' : '#ffffff')}
              stroke-width={isSelected ? 2 : node.type === 'document' || node.type === 'collection' ? 2.5 : 0.8}
              class="transition-transform duration-150"
              style="filter: drop-shadow(0 1px 2px rgba(0,0,0,{isDarkMode ? '0.5' : '0.15'}));"
            />
          </g>
        {/each}
      </g>
    </svg>

    <!-- Empty State / Backend Connection Prompt if Offline -->
    {#if !isBackendLive}
      <div class="absolute inset-0 flex items-center justify-center p-6 pointer-events-none">
        <div class="max-w-md {isDarkMode ? 'bg-[#0e1424]/95 border-red-500/20' : 'bg-white/95 border-red-300 shadow-xl'} border backdrop-blur-md p-6 rounded-2xl text-center space-y-3 pointer-events-auto">
          <div class="w-10 h-10 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mx-auto border border-red-500/20">
            <AlertCircle class="w-5 h-5" />
          </div>
          <h2 class="text-sm font-semibold {isDarkMode ? 'text-neutral-100' : 'text-slate-900'}">Milvus Service Offline</h2>
          <p class="text-xs {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} leading-relaxed">
            The FastAPI Milvus bridge at <code class="text-blue-500 font-mono">http://localhost:8080</code> is not connected.
          </p>
          <button
            type="button"
            onclick={() => {
              checkBackendHealth();
              if (hasSearched && activeSearchQuery) handleSearch();
            }}
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      </div>
    {:else if !hasSearched && !isSearching}
      <!-- INITIAL PROMPT USER STATE (No default graph displayed, asks user to prompt) -->
      <div class="absolute inset-0 flex items-center justify-center p-6 pointer-events-none">
        <div class="max-w-lg w-full {isDarkMode ? 'bg-[#0e1424]/90 border-neutral-800 text-neutral-100 shadow-2xl' : 'bg-white/95 border-slate-200 text-slate-800 shadow-xl'} border backdrop-blur-md p-8 rounded-2xl text-center space-y-4 pointer-events-auto transition-all animate-in fade-in duration-200">
          <div class="w-14 h-14 rounded-2xl {isDarkMode ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-blue-50 text-blue-600 border-blue-200'} flex items-center justify-center mx-auto border shadow-sm">
            <Sparkles class="w-7 h-7" />
          </div>
          <div class="space-y-1.5">
            <h2 class="text-base font-semibold {isDarkMode ? 'text-neutral-100' : 'text-slate-900'} tracking-tight">
              Search Milvus Vector Graph
            </h2>
            <p class="text-xs {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} leading-relaxed max-w-sm mx-auto">
              Enter a search query or prompt above to project 384-dimensional vector embeddings into interactive semantic clusters.
            </p>
          </div>

          <div class="pt-2 space-y-2.5 border-t {isDarkMode ? 'border-neutral-800/80' : 'border-slate-100'}">
            <span class="text-[11px] font-mono {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} block">
              Suggested queries to explore:
            </span>
            <div class="flex flex-wrap items-center justify-center gap-1.5">
              {#each SUGGESTED_QUERIES as q}
                <button
                  type="button"
                  onclick={() => {
                    searchQuery = q;
                    handleSearch();
                  }}
                  class="px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-all cursor-pointer {isDarkMode ? 'bg-[#131b2e] hover:bg-[#1e2a47] text-neutral-300 hover:text-blue-300 border-neutral-800' : 'bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-600 border-slate-200'}"
                >
                  {q}
                </button>
              {/each}
            </div>
          </div>
        </div>
      </div>
    {:else if isSearching}
      <div class="absolute inset-0 flex items-center justify-center p-6 pointer-events-none">
        <div class="flex items-center gap-3 px-5 py-3 rounded-2xl border backdrop-blur-md {isDarkMode ? 'bg-[#0e1424]/95 border-neutral-800 text-neutral-200 shadow-xl' : 'bg-white/95 border-slate-200 text-slate-800 shadow-xl'} pointer-events-auto animate-pulse">
          <RefreshCw class="w-4 h-4 animate-spin text-blue-500" />
          <span class="text-xs font-medium">Embedding query & retrieving nearest vectors...</span>
        </div>
      </div>
    {:else if hasSearched && nodes.filter(n => !n.is_center && n.type !== 'query').length === 0 && !isSearching}
      <div class="absolute inset-0 flex items-center justify-center p-6 pointer-events-none">
        <div class="max-w-sm {isDarkMode ? 'bg-[#0e1424]/95 border-neutral-800' : 'bg-white/95 border-slate-200 shadow-xl'} border backdrop-blur-md p-6 rounded-2xl text-center space-y-3 pointer-events-auto">
          <Database class="w-8 h-8 text-neutral-400 mx-auto" />
          <h2 class="text-sm font-semibold {isDarkMode ? 'text-neutral-200' : 'text-slate-800'}">No Matching Vectors</h2>
          <p class="text-xs {isDarkMode ? 'text-neutral-400' : 'text-slate-500'}">
            No vectors matched "{activeSearchQuery}" in this collection.
          </p>
          <button
            type="button"
            onclick={handleReset}
            class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium cursor-pointer"
          >
            Clear Search
          </button>
        </div>
      </div>
    {/if}

    <!-- Floating Node Hover Tooltip -->
    {#if hoveredNode}
      {@const cx = canvasWidth / 2}
      {@const cy = canvasHeight / 2}
      {@const screenX = panX + cx * (1 - zoom) + hoveredNode.x * zoom}
      {@const screenY = panY + cy * (1 - zoom) + hoveredNode.y * zoom}
      <div
        class="absolute pointer-events-none z-30 transition-all duration-75"
        style="left: {screenX}px; top: {screenY - 14}px; transform: translate(-50%, -100%);"
      >
        <div class="{isDarkMode ? 'bg-[#0f172a]/95 border-neutral-700/80 text-neutral-100 shadow-2xl' : 'bg-white/95 border-slate-200 text-slate-800 shadow-xl'} backdrop-blur-md px-3 py-2 rounded-lg border text-xs space-y-1 max-w-xs animate-in fade-in duration-100">
          <div class="flex items-center gap-1.5 font-semibold truncate">
            <span class="w-2 h-2 rounded-full shrink-0" style="background-color: {hoveredNode.color};"></span>
            <span class="truncate">{hoveredNode.meta?.doc_name || hoveredNode.meta?.title || hoveredNode.label}</span>
          </div>
          <div class="flex items-center justify-between gap-3 text-[10px] {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} font-mono">
            <span class="capitalize">{hoveredNode.type === 'query' ? 'Query Vector' : hoveredNode.type === 'document' ? 'Document Centroid' : 'Vector Chunk'}</span>
            {#if hoveredNode.semantic_x !== undefined && hoveredNode.semantic_y !== undefined}
              <span class="text-blue-400 font-mono">[{hoveredNode.semantic_x.toFixed(2)}, {hoveredNode.semantic_y.toFixed(2)}]</span>
            {/if}
            {#if hoveredNode.similarity_pct}
              <span class="text-emerald-500 font-bold">{hoveredNode.similarity_pct}% match</span>
            {:else if hoveredNode.score}
              <span class="text-emerald-500 font-bold">{(hoveredNode.score * 100).toFixed(1)}% match</span>
            {:else if hoveredNode.meta?.page_number}
              <span>Page {hoveredNode.meta.page_number}</span>
            {/if}
          </div>
        </div>
      </div>
    {:else if hoveredEdge}
      <!-- Floating Edge Hover Tooltip (Only shown on hover, zero canvas clutter) -->
      {@const cx = canvasWidth / 2}
      {@const cy = canvasHeight / 2}
      {@const midX = (hoveredEdge.sourceNode.x + hoveredEdge.targetNode.x) / 2}
      {@const midY = (hoveredEdge.sourceNode.y + hoveredEdge.targetNode.y) / 2}
      {@const screenX = panX + cx * (1 - zoom) + midX * zoom}
      {@const screenY = panY + cy * (1 - zoom) + midY * zoom}
      <div
        class="absolute pointer-events-none z-30 transition-all duration-75"
        style="left: {screenX}px; top: {screenY - 12}px; transform: translate(-50%, -100%);"
      >
        <div class="{isDarkMode ? 'bg-[#0f172a]/95 border-purple-500/40 text-neutral-100 shadow-2xl' : 'bg-white/95 border-purple-200 text-slate-800 shadow-xl'} backdrop-blur-md px-3 py-1.5 rounded-lg border text-xs space-y-0.5 animate-in fade-in duration-100">
          <div class="flex items-center gap-1.5 font-semibold text-[11px]">
            <span class="w-1.5 h-1.5 rounded-full {hoveredEdge.type === 'bridge' ? 'bg-purple-500' : 'bg-blue-500'}"></span>
            <span>{hoveredEdge.label || (hoveredEdge.type === 'bridge' ? 'Semantic Bridge' : 'Relationship')}</span>
          </div>
          {#if hoveredEdge.similarity}
            <div class="text-[10px] font-mono {isDarkMode ? 'text-purple-300' : 'text-purple-600'}">
              Cosine Similarity: {(hoveredEdge.similarity * 100).toFixed(1)}%
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Minimalist Canvas Floating Navigation Controls & Legend (shown when searched & active) -->
    {#if hasSearched && nodes.filter(n => !n.is_center && n.type !== 'query').length > 0}
      <div class="absolute bottom-5 right-6 flex items-center {isDarkMode ? 'bg-[#0e1424]/90 border-neutral-800 text-neutral-400' : 'bg-white/90 border-slate-200 text-slate-600 shadow-md'} border backdrop-blur-md p-1 rounded-xl text-xs z-10 transition-colors">
        <button
          type="button"
          onclick={() => (zoom = Math.min(2.8, zoom * 1.15))}
          class="p-2 {isDarkMode ? 'hover:text-neutral-100 hover:bg-neutral-800/60' : 'hover:text-slate-900 hover:bg-slate-100'} rounded-lg transition-colors"
          title="Zoom In"
        >
          <ZoomIn class="w-4 h-4" />
        </button>
        <button
          type="button"
          onclick={() => (zoom = Math.max(0.4, zoom * 0.85))}
          class="p-2 {isDarkMode ? 'hover:text-neutral-100 hover:bg-neutral-800/60' : 'hover:text-slate-900 hover:bg-slate-100'} rounded-lg transition-colors"
          title="Zoom Out"
        >
          <ZoomOut class="w-4 h-4" />
        </button>
        <button
          type="button"
          onclick={resetViewport}
          class="p-2 {isDarkMode ? 'hover:text-neutral-100 hover:bg-neutral-800/60 border-neutral-800' : 'hover:text-slate-900 hover:bg-slate-100 border-slate-200'} rounded-lg transition-colors border-l"
          title="Reset Center View"
        >
          <Maximize2 class="w-4 h-4" />
        </button>
      </div>

      <!-- Attu Vector Space Legend -->
      <div class="absolute bottom-5 left-6 pointer-events-none text-[11px] font-mono {isDarkMode ? 'bg-[#0e1424]/90 border-neutral-800/80 text-neutral-400' : 'bg-white/95 border-slate-200 text-slate-600 shadow-md'} space-y-1.5 p-3 rounded-xl border backdrop-blur-md z-10 transition-colors">
        <div class="flex items-center justify-between gap-4 font-semibold text-[10px] uppercase tracking-wider {isDarkMode ? 'text-neutral-300' : 'text-slate-700'} border-b {isDarkMode ? 'border-neutral-800' : 'border-slate-200'} pb-1">
          <span>Attu Vector Space</span>
          <span class="text-blue-500 font-mono text-[9px]">384d → 2D SVD</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full {isDarkMode ? 'bg-[#38bdf8]' : 'bg-[#0284c7]'}"></span>
          <span>Query Center</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-[#10b981]"></span>
          <span>Nearest Neighbors (>65%)</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-purple-500"></span>
          <span>Inter-Doc Bridge</span>
        </div>
        <div class="pt-1 border-t {isDarkMode ? 'border-neutral-800/80 text-neutral-500' : 'border-slate-200 text-slate-400'} text-[10px]">
          Query match links • Vector proximity
        </div>
      </div>
    {/if}

    <!-- ========================================================================= -->
    <!-- ENTERPRISE NODE INSPECTOR DRAWER -->
    <!-- ========================================================================= -->
    {#if selectedNode}
      {@const meta = selectedNode.meta || {}}
      {@const matchingDoc = findMatchingDoc(meta.doc_name || selectedNode.label || '')}
      <aside class="w-84 sm:w-96 {isDarkMode ? 'bg-[#0c1220]/95 border-neutral-800/90 text-neutral-100' : 'bg-white/95 border-slate-200 text-slate-800 shadow-2xl'} border-l flex flex-col justify-between p-5 backdrop-blur-md z-30 animate-in slide-in-from-right-8 duration-200 transition-colors">
        <div class="space-y-4 overflow-y-auto custom-scrollbar pr-1">
          <!-- Drawer Header -->
          <div class="flex items-center justify-between border-b {isDarkMode ? 'border-neutral-800/80' : 'border-slate-200'} pb-3">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full" style="background-color: {selectedNode.color};"></span>
              <span class="text-xs font-semibold uppercase tracking-wider {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} font-mono">
                {selectedNode.type === 'query'
                  ? 'Query Vector'
                  : selectedNode.type === 'collection'
                    ? 'Milvus Collection'
                    : 'Milvus Vector Chunk'}
              </span>
            </div>
            <button
              type="button"
              onclick={() => (selectedNode = null)}
              class="p-1 rounded-md {isDarkMode ? 'text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800' : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'} transition-colors cursor-pointer"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Semantic Relevance Gauge (If Search Result) -->
          {#if selectedNode.similarity_pct}
            <div class="p-3.5 rounded-xl {isDarkMode ? 'bg-[#121929] border-neutral-800' : 'bg-slate-50 border-slate-200'} border space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium {isDarkMode ? 'text-neutral-300' : 'text-slate-700'}">
                  {meta.relevance_tier || 'Semantic Match'}
                </span>
                <span
                  class="text-xs font-bold font-mono px-2 py-0.5 rounded"
                  style="background-color: {selectedNode.color}20; color: {selectedNode.color}; border: 1px solid {selectedNode.color}40;"
                >
                  {selectedNode.similarity_pct}% Match
                </span>
              </div>
              <div class="w-full {isDarkMode ? 'bg-neutral-800' : 'bg-slate-200'} h-1.5 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  style="width: {selectedNode.similarity_pct}%; background-color: {selectedNode.color};"
                ></div>
              </div>
              <div class="text-[10px] {isDarkMode ? 'text-neutral-500' : 'text-slate-400'} font-mono flex items-center justify-between">
                <span>Distance: {selectedNode.score?.toFixed(4) || 'N/A'}</span>
                <span>HNSW Cosine</span>
              </div>
            </div>
          {/if}

          <!-- Document & Page Location Details -->
          <div class="space-y-1.5">
            <h3 class="text-sm font-semibold {isDarkMode ? 'text-neutral-100' : 'text-slate-900'} leading-snug">
              {meta.doc_name || meta.title || selectedNode.label}
            </h3>

            <div class="flex flex-wrap items-center gap-2 text-xs font-mono {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} pt-1">
              {#if meta.collection_name}
                <span class="px-2 py-0.5 rounded {isDarkMode ? 'bg-neutral-800/80 text-neutral-300' : 'bg-slate-100 text-slate-700'}">
                  {meta.collection_name}
                </span>
              {/if}
              {#if meta.page_number}
                <span class="px-2 py-0.5 rounded {isDarkMode ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-blue-50 text-blue-600 border border-blue-200'}">
                  Page {meta.page_number}
                </span>
              {/if}
              {#if meta.chunk_index}
                <span class="px-2 py-0.5 rounded {isDarkMode ? 'bg-neutral-800/80 text-neutral-300' : 'bg-slate-100 text-slate-700'}">
                  Chunk #{meta.chunk_index}
                </span>
              {/if}
              {#if meta.char_count}
                <span class="opacity-70">
                  {meta.char_count} chars
                </span>
              {/if}
              {#if meta.chunks_count !== undefined}
                <span class="px-2 py-0.5 rounded {isDarkMode ? 'bg-purple-950/40 text-purple-300 border border-purple-800/50' : 'bg-purple-50 text-purple-700 border border-purple-200'}">
                  {meta.chunks_count} / {meta.total_chunks || meta.chunks_count} chunks rendered
                </span>
              {/if}
            </div>
          </div>

          <!-- Document Chunk Cap Indicator & Uncap Action -->
          {#if selectedNode.type === 'document' && meta.total_chunks && meta.chunks_count < meta.total_chunks}
            <div class="p-3 rounded-xl border {isDarkMode ? 'bg-amber-950/20 border-amber-800/40 text-amber-200' : 'bg-amber-50 border-amber-200 text-amber-800'} space-y-2 text-xs">
              <div class="font-medium flex items-center justify-between">
                <span>Displaying {meta.chunks_count} of {meta.total_chunks} chunks</span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20">Capped</span>
              </div>
              <p class="text-[11px] opacity-80 leading-relaxed">
                By default, chunk density is capped to keep SVG canvas physics at 60 FPS.
              </p>
              <button
                type="button"
                onclick={() => {
                  chunksLimit = 0;
                  selectedCollectionId = meta.collection_name || selectedCollectionId;
                  loadGraphData();
                }}
                class="w-full py-1.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs transition-colors cursor-pointer text-center"
              >
                Load All {meta.total_chunks} Chunks
              </button>
            </div>
          {/if}

          <!-- Real Text Passage Stored in Milvus -->
          {#if meta.text || meta.excerpt}
            <div class="space-y-1.5">
              <div class="text-[11px] font-semibold {isDarkMode ? 'text-neutral-400' : 'text-slate-500'} uppercase tracking-wider font-mono">
                Milvus Vector Payload
              </div>
              <div class="p-3.5 rounded-xl {isDarkMode ? 'bg-[#090d16] border-neutral-800 text-neutral-300' : 'bg-slate-50 border-slate-200 text-slate-700'} border text-xs leading-relaxed font-sans max-h-52 overflow-y-auto custom-scrollbar italic border-l-2" style="border-left-color: {selectedNode.color};">
                "{meta.text || meta.excerpt}"
              </div>
            </div>
          {/if}

          <!-- Metadata Source Badge -->
          <div class="text-[10px] font-mono {isDarkMode ? 'text-neutral-500' : 'text-slate-400'} flex items-center gap-1.5 pt-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Source: Milvus Standalone (Live)</span>
          </div>
        </div>

        <!-- Action Footer -->
        <div class="pt-4 border-t {isDarkMode ? 'border-neutral-800/80' : 'border-slate-200'} space-y-2 shrink-0">
          {#if matchingDoc}
            <button
              type="button"
              onclick={() => onOpenDocument(matchingDoc, meta.page_number || 1)}
              class="w-full flex items-center justify-center gap-2 py-2.5 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors cursor-pointer"
            >
              <Eye class="w-3.5 h-3.5" />
              <span>Open in PDF Viewer</span>
            </button>
          {/if}

          <button
            type="button"
            onclick={() =>
              handleCopyCitation(
                meta.citation || `${meta.doc_name || meta.title} (Page ${meta.page_number || 1})`
              )}
            class="w-full flex items-center justify-center gap-1.5 py-2 px-3 {isDarkMode ? 'bg-[#121929] hover:bg-[#1a253e] text-neutral-300 border-neutral-800' : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'} rounded-xl text-xs font-medium border transition-colors cursor-pointer"
          >
            {#if copiedCitation}
              <Check class="w-3.5 h-3.5 text-emerald-500" />
              <span class="text-emerald-500">Citation Copied!</span>
            {:else}
              <Copy class="w-3.5 h-3.5" />
              <span>Copy Citation</span>
            {/if}
          </button>
        </div>
      </aside>
    {/if}
  </div>
</div>
