<script lang="ts">
  import {
    Network,
    Search,
    ZoomIn,
    ZoomOut,
    RotateCcw,
    SlidersHorizontal,
    ExternalLink,
    FileText,
    ArrowRight,
    Folder,
    Globe,
    Eye,
    ChevronRight,
    Share2
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, UserProfile, EdgeDefinitionMode } from '../types';
  import { computeDocumentGraph } from '../utils/retrieval';
  import { isCollectionAccessible } from '../utils/governance';
  import { formatBytes } from '../utils/resourceUtils';

  interface Props {
    collection: Collection;
    allDocuments: DocumentItem[];
    collections?: Collection[];
    currentUser?: UserProfile;
    selectedDocId?: string | null;
    onOpenDocument: (doc: DocumentItem, pageNumber?: number, chunkId?: string) => void;
  }

  let {
    collection,
    allDocuments = [],
    collections = [],
    currentUser,
    selectedDocId = null,
    onOpenDocument
  }: Props = $props();

  // Color generator based on string hash for harmonious, distinct document nodes
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

  function getDocColor(identifier: string, isDark: boolean): string {
    if (!identifier) return isDark ? '#38bdf8' : '#0284c7';
    let hash = 0;
    const str = identifier.trim().toLowerCase();
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
      hash |= 0;
    }
    const hue = Math.abs(hash) % 360;
    return hslToHex(hue, 70, isDark ? 55 : 42);
  }

  // Theme Detection
  let isDarkMode = $state(
    typeof document !== 'undefined'
      ? document.documentElement.classList.contains('dark')
      : true
  );

  $effect(() => {
    if (typeof MutationObserver !== 'undefined' && typeof document !== 'undefined') {
      const observer = new MutationObserver(() => {
        isDarkMode = document.documentElement.classList.contains('dark');
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
      return () => observer.disconnect();
    }
  });

  // Controls State
  let includeExternalDocs = $state(false);
  let edgeMode = $state<EdgeDefinitionMode>('combined');
  let similarityThreshold = $state(0.18);
  let searchQuery = $state('');
  let isInspectorOpen = $state(true);

  // Viewport / Pan & Zoom
  let canvasContainer = $state<HTMLDivElement | null>(null);
  let canvasWidth = $state(900);
  let canvasHeight = $state(600);
  let zoom = $state(1.0);
  let panX = $state(0);
  let panY = $state(0);
  let isDraggingCanvas = $state(false);
  let dragStartX = $state(0);
  let dragStartY = $state(0);
  let mouseDownClientX = 0;
  let mouseDownClientY = 0;
  let hasDraggedCanvas = false;

  // Node Dragging & Selection
  let draggedNode = $state<any | null>(null);
  let activeFocusDocId = $state<string | null>(null);
  let hoveredNode = $state<any | null>(null);
  let hoveredEdge = $state<any | null>(null);

  $effect(() => {
    if (selectedDocId) {
      activeFocusDocId = selectedDocId;
    }
  });

  // Filter in-collection docs
  let inCollectionDocs = $derived(allDocuments.filter((d) => d.collectionId === collection.id));

  // External Accessible Documents (filtered by RBAC)
  let accessibleExternalDocs = $derived.by(() => {
    const colMap = new Map<string, Collection>(collections.map((c) => [c.id, c]));
    return allDocuments.filter((doc) => {
      if (doc.collectionId === collection.id) return false;
      const docCol = colMap.get(doc.collectionId);
      if (!docCol) return false;
      return isCollectionAccessible(currentUser, docCol);
    });
  });

  // Non-reactive position cache across re-computations to avoid jumping
  const positionCache = new Map<string, { x: number; y: number }>();

  // Graph Structure (Nodes + Edges with pre-linked sourceNode/targetNode)
  interface GraphEdgeLinked {
    source: string;
    target: string;
    weight: number;
    reasons: string[];
    type: string;
    sourceNode: any;
    targetNode: any;
  }

  let nodes = $state<any[]>([]);
  let edges = $state<GraphEdgeLinked[]>([]);
  let nodeMap = $derived(new Map<string, any>(nodes.map((n) => [n.id, n])));

  // Single-pass Graph & Layout Builder
  function buildGraphLayout() {
    const colMap = new Map<string, Collection>(collections.map((c) => [c.id, c]));
    const inColIds = new Set(inCollectionDocs.map((d) => d.id));

    let candidateDocs: DocumentItem[];
    if (!includeExternalDocs) {
      candidateDocs = inCollectionDocs;
    } else {
      // Evaluate all accessible docs once
      const combined = [...inCollectionDocs, ...accessibleExternalDocs];
      const rawGraph = computeDocumentGraph(combined, edgeMode, similarityThreshold);

      const connectedExternalIds = new Set<string>();
      for (const e of rawGraph.edges) {
        if (inColIds.has(e.source) && !inColIds.has(e.target)) {
          connectedExternalIds.add(e.target);
        } else if (!inColIds.has(e.source) && inColIds.has(e.target)) {
          connectedExternalIds.add(e.source);
        }
      }
      const validExternal = accessibleExternalDocs.filter((d) => connectedExternalIds.has(d.id));
      candidateDocs = [...inCollectionDocs, ...validExternal];
    }

    // Compute final graph
    const computed = computeDocumentGraph(candidateDocs, edgeMode, similarityThreshold);

    const cx = canvasWidth / 2;
    const cy = canvasHeight / 2;
    const radius = Math.min(canvasWidth, canvasHeight) * 0.32;
    const count = candidateDocs.length;

    // Create node objects with initial target coordinates
    const newNodes = candidateDocs.map((doc, idx) => {
      const isInternal = doc.collectionId === collection.id;
      const docCol = colMap.get(doc.collectionId);
      const colName = isInternal ? collection.name : docCol?.name || 'External Collection';

      let initialX = cx;
      let initialY = cy;

      const cached = positionCache.get(doc.id);
      if (cached) {
        initialX = cached.x;
        initialY = cached.y;
      } else {
        const angle = (idx / Math.max(1, count)) * 2 * Math.PI;
        const dist = isInternal ? radius * 0.5 : radius * 0.88;
        initialX = cx + Math.cos(angle) * dist;
        initialY = cy + Math.sin(angle) * dist;
      }

      return {
        id: doc.id,
        doc,
        title: doc.title,
        fileType: doc.fileType,
        pageCount: doc.pageCount,
        chunkCount: doc.chunkCount,
        collectionId: doc.collectionId,
        collectionName: colName,
        isInternal,
        color: isInternal
          ? (collection.colorTheme || getDocColor(doc.title, isDarkMode))
          : getDocColor(colName + doc.title, isDarkMode),
        radius: isInternal ? 20 : 16,
        x: initialX,
        y: initialY,
        targetX: initialX,
        targetY: initialY
      };
    });

    // 25 iterations of instant relaxation so nodes never overlap
    const minDistance = 50;
    for (let iter = 0; iter < 25; iter++) {
      for (let i = 0; i < newNodes.length; i++) {
        for (let j = i + 1; j < newNodes.length; j++) {
          const n1 = newNodes[i];
          const n2 = newNodes[j];
          const dx = n2.targetX - n1.targetX;
          const dy = n2.targetY - n1.targetY;
          const dist = Math.hypot(dx, dy) || 1;
          const reqDist = n1.radius + n2.radius + minDistance;

          if (dist < reqDist) {
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

    // Soft bounds clamp
    for (const node of newNodes) {
      node.targetX = Math.max(node.radius + 30, Math.min(canvasWidth - node.radius - 30, node.targetX));
      node.targetY = Math.max(node.radius + 30, Math.min(canvasHeight - node.radius - 30, node.targetY));
      positionCache.set(node.id, { x: node.targetX, y: node.targetY });
    }

    // Build pre-linked edges ($O(1) lookup in render loop)
    const tempNodeMap = new Map<string, any>(newNodes.map((n) => [n.id, n]));
    const linkedEdges: GraphEdgeLinked[] = [];
    for (const rawEdge of computed.edges) {
      const srcNode = tempNodeMap.get(rawEdge.source);
      const tgtNode = tempNodeMap.get(rawEdge.target);
      if (srcNode && tgtNode) {
        linkedEdges.push({
          ...rawEdge,
          sourceNode: srcNode,
          targetNode: tgtNode
        });
      }
    }

    nodes = newNodes;
    edges = linkedEdges;

    if (!activeFocusDocId && newNodes.length > 0) {
      activeFocusDocId = newNodes[0].id;
    }

    triggerMotionAnimation();
  }

  // Reactive trigger for graph computation (cleanly isolated, zero loops)
  $effect(() => {
    // Explicit dependencies
    const _col = collection.id;
    const _all = allDocuments.length;
    const _ext = includeExternalDocs;
    const _mode = edgeMode;
    const _thresh = similarityThreshold;
    const _w = canvasWidth;
    const _h = canvasHeight;

    buildGraphLayout();
  });

  // Gliding Animation Loop (Only active when moving, 0% CPU when settled)
  let isGliding = false;
  let animFrameId: number | null = null;

  function triggerMotionAnimation() {
    if (isGliding) return;
    isGliding = true;

    function step() {
      let hasMovement = false;

      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        if (node === draggedNode) continue;

        const dx = node.targetX - node.x;
        const dy = node.targetY - node.y;

        if (Math.abs(dx) > 0.15 || Math.abs(dy) > 0.15) {
          node.x += dx * 0.16;
          node.y += dy * 0.16;
          hasMovement = true;
        } else {
          node.x = node.targetX;
          node.y = node.targetY;
        }
      }

      if (hasMovement || draggedNode) {
        nodes = [...nodes];
        animFrameId = requestAnimationFrame(step);
      } else {
        isGliding = false;
        animFrameId = null;
      }
    }

    animFrameId = requestAnimationFrame(step);
  }

  $effect(() => {
    return () => {
      if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
        isGliding = false;
      }
    };
  });

  // Canvas Viewport Controls
  function resetViewport() {
    zoom = 1.0;
    panX = 0;
    panY = 0;
  }

  function onMouseDownCanvas(e: MouseEvent) {
    mouseDownClientX = e.clientX;
    mouseDownClientY = e.clientY;
    hasDraggedCanvas = false;

    const target = e.target as HTMLElement;
    if (target.tagName !== 'svg' && target.id !== 'graph-bg') return;
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
      positionCache.set(draggedNode.id, { x: worldX, y: worldY });
      triggerMotionAnimation();
    }
  }

  function onMouseUpCanvas() {
    isDraggingCanvas = false;
    draggedNode = null;
  }

  function onWheelCanvas(e: WheelEvent) {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    zoom = Math.max(0.4, Math.min(2.8, zoom * zoomFactor));
  }

  // Focus Document & Relationship Data for Inspector
  let activeFocusNode = $derived(
    (activeFocusDocId && nodeMap.get(activeFocusDocId)) || nodes[0] || null
  );

  let activeFocusDoc = $derived(activeFocusNode?.doc || null);

  let activeConnectedEdges = $derived.by(() => {
    if (!activeFocusDocId) return [];
    return edges.filter(
      (e) => e.source === activeFocusDocId || e.target === activeFocusDocId
    );
  });

  let rankedRelatedDocs = $derived.by(() => {
    if (!activeFocusDocId) return [];
    const list: { node: any; edge: GraphEdgeLinked; similarity: number }[] = [];

    for (const edge of activeConnectedEdges) {
      const otherNode = edge.source === activeFocusDocId ? edge.targetNode : edge.sourceNode;
      if (otherNode) {
        list.push({
          node: otherNode,
          edge,
          similarity: Math.round(edge.weight * 100)
        });
      }
    }
    return list.sort((a, b) => b.similarity - a.similarity);
  });

  // Filtered nodes based on search query
  let searchMatchingNodeIds = $derived.by(() => {
    if (!searchQuery.trim()) return null;
    const q = searchQuery.toLowerCase();
    const matchIds = new Set<string>();
    for (const n of nodes) {
      if (
        n.title.toLowerCase().includes(q) ||
        n.collectionName.toLowerCase().includes(q) ||
        n.doc.summary.toLowerCase().includes(q) ||
        n.doc.entities.some((e: string) => e.toLowerCase().includes(q))
      ) {
        matchIds.add(n.id);
      }
    }
    return matchIds;
  });

  let externalAvailableCount = $derived(accessibleExternalDocs.length);
  let externalConnectedCount = $derived(nodes.filter((n) => !n.isInternal).length);
</script>

<div class="flex-1 flex flex-col h-full overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors select-none">
  <!-- ========================================================================= -->
  <!-- TOP CONTROLS & SCOPE TOOLBAR -->
  <!-- ========================================================================= -->
  <div class="h-13 px-4 sm:px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex flex-wrap items-center justify-between gap-3 shrink-0 z-10">
    <div class="flex items-center gap-2.5">
      <div class="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 flex items-center justify-center text-blue-600 dark:text-blue-400">
        <Network class="w-4 h-4" />
      </div>
      <div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold text-neutral-900 dark:text-neutral-100">
            Document Vector Graph
          </span>
          <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-500 border border-neutral-200 dark:border-neutral-700">
            {nodes.length} {nodes.length === 1 ? 'doc' : 'docs'} · {edges.length} edges
          </span>
        </div>
      </div>
    </div>

    <!-- Center/Right Controls: Hybrid Scope Toggle, Relation Mode, Threshold, Search -->
    <div class="flex items-center gap-2 text-xs">
      <!-- 1. Hybrid Scope Toggle: Collection Only vs Include Accessible Docs -->
      <div class="flex items-center p-0.5 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
        <button
          type="button"
          onclick={() => (includeExternalDocs = false)}
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer {
            !includeExternalDocs
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
          }"
          title="Display only documents contained inside this collection"
        >
          <Folder class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
          <span>In Collection ({inCollectionDocs.length})</span>
        </button>

        <button
          type="button"
          onclick={() => (includeExternalDocs = true)}
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer {
            includeExternalDocs
              ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-2xs font-semibold'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200'
          }"
          title="Include accessible related documents across other collections you have permission to view"
        >
          <Globe class="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
          <span>+ Accessible Docs ({includeExternalDocs ? externalConnectedCount : `+${externalAvailableCount}`})</span>
        </button>
      </div>

      <!-- 2. Relationship Edge Mode -->
      <div class="hidden md:flex items-center gap-1 px-2 py-1 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
        <SlidersHorizontal class="w-3.5 h-3.5 text-neutral-400" />
        <select
          bind:value={edgeMode}
          class="bg-transparent outline-none cursor-pointer text-[11px] font-medium text-neutral-700 dark:text-neutral-300 pr-1"
          title="Algorithm used to compute cross-document similarity"
        >
          <option value="combined">Hybrid Vector & Entities</option>
          <option value="semantic">Semantic Topics</option>
          <option value="entities">Entity Co-occurrence</option>
          <option value="cross-references">Direct References</option>
        </select>
      </div>

      <!-- 3. Similarity Threshold Slider -->
      <div class="hidden lg:flex items-center gap-1.5 px-2.5 py-1 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 text-[11px] font-mono">
        <span class="text-neutral-400">Match:</span>
        <input
          type="range"
          min="0.10"
          max="0.60"
          step="0.02"
          bind:value={similarityThreshold}
          class="w-16 accent-blue-600 cursor-pointer"
          title="Adjust similarity cutoff threshold"
        />
        <span class="text-neutral-700 dark:text-neutral-300 font-semibold">{Math.round(similarityThreshold * 100)}%</span>
      </div>

      <!-- 4. Quick Search Filter -->
      <div class="relative w-36 sm:w-44">
        <Search class="w-3.5 h-3.5 text-neutral-400 absolute left-2 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Filter graph docs..."
          bind:value={searchQuery}
          class="w-full pl-7 pr-2 py-1 text-xs bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-hidden focus:border-blue-500"
        />
      </div>

      <!-- 5. Toggle Inspector Button -->
      <button
        type="button"
        onclick={() => (isInspectorOpen = !isInspectorOpen)}
        class="p-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 bg-white dark:bg-neutral-800 cursor-pointer transition-colors"
        title={isInspectorOpen ? 'Collapse inspector panel' : 'Open inspector panel'}
      >
        <Eye class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- MAIN GRAPH WORKSPACE + INSPECTOR -->
  <!-- ========================================================================= -->
  <div class="flex-1 flex overflow-hidden relative">
    <!-- SVG Interactive Canvas -->
    <div
      bind:this={canvasContainer}
      bind:clientWidth={canvasWidth}
      bind:clientHeight={canvasHeight}
      class="flex-1 h-full overflow-hidden relative bg-neutral-100/50 dark:bg-[#070b14]"
    >
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <svg
        id="collection-graph-canvas"
        class="w-full h-full cursor-grab active:cursor-grabbing select-none"
        onmousedown={onMouseDownCanvas}
        onmousemove={onMouseMoveCanvas}
        onmouseup={onMouseUpCanvas}
        onwheel={onWheelCanvas}
        onclick={() => {
          if (!hasDraggedCanvas) {
            hoveredEdge = null;
          }
          hasDraggedCanvas = false;
        }}
      >
        <rect id="graph-bg" width="100%" height="100%" fill="transparent" />

        <!-- Transformable Layer -->
        <g transform="translate({panX + (canvasWidth / 2) * (1 - zoom)}, {panY + (canvasHeight / 2) * (1 - zoom)}) scale({zoom})">
          <!-- Edges between documents (pre-linked, zero array.find in template) -->
          {#each edges as edge}
            {@const srcNode = edge.sourceNode}
            {@const tgtNode = edge.targetNode}
            {#if srcNode && tgtNode}
              {@const isConnectedToFocus = activeFocusDocId === srcNode.id || activeFocusDocId === tgtNode.id}
              {@const isHoveredEdge = (hoveredNode && (hoveredNode.id === srcNode.id || hoveredNode.id === tgtNode.id)) || (hoveredEdge && hoveredEdge.source === edge.source && hoveredEdge.target === edge.target)}
              {@const isActive = isConnectedToFocus || isHoveredEdge}
              {@const isCrossCollection = !srcNode.isInternal || !tgtNode.isInternal}
              {@const strokeColor = isActive
                ? (isDarkMode ? '#38bdf8' : '#0284c7')
                : isCrossCollection
                ? (isDarkMode ? '#818cf8' : '#6366f1')
                : (isDarkMode ? '#475569' : '#cbd5e1')}
              {@const strokeWidth = isActive ? 2.0 : Math.max(0.8, edge.weight * 2.2)}
              {@const strokeOpacity = isActive ? 0.9 : isCrossCollection ? 0.35 : 0.22}

              <!-- Visible Line -->
              <line
                x1={srcNode.x}
                y1={srcNode.y}
                x2={tgtNode.x}
                y2={tgtNode.y}
                stroke={strokeColor}
                stroke-width={strokeWidth}
                stroke-opacity={strokeOpacity}
                stroke-dasharray={isCrossCollection ? '4 3' : 'none'}
                class="transition-opacity duration-150 pointer-events-none"
              />

              <!-- Hit Area for Tooltip -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <line
                x1={srcNode.x}
                y1={srcNode.y}
                x2={tgtNode.x}
                y2={tgtNode.y}
                stroke="transparent"
                stroke-width="16"
                class="cursor-pointer"
                onmouseenter={() => (hoveredEdge = { ...edge, srcTitle: srcNode.title, tgtTitle: tgtNode.title })}
                onmouseleave={() => {
                  if (hoveredEdge?.source === edge.source && hoveredEdge?.target === edge.target) {
                    hoveredEdge = null;
                  }
                }}
              />
            {/if}
          {/each}

          <!-- Document Nodes (Only Documents) -->
          {#each nodes as node (node.id)}
            {@const isFocus = activeFocusDocId === node.id}
            {@const isHovered = hoveredNode?.id === node.id}
            {@const isConnected = activeConnectedEdges.some((e) => e.source === node.id || e.target === node.id)}
            {@const isSearchMatch = searchMatchingNodeIds === null || searchMatchingNodeIds.has(node.id)}
            {@const isDimmed = (searchMatchingNodeIds !== null && !isSearchMatch) || (activeFocusDocId && !isFocus && !isConnected && !isHovered)}
            {@const nodeOpacity = isDimmed ? 0.25 : 1.0}

            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <g
              transform="translate({node.x}, {node.y})"
              class="cursor-pointer group transition-opacity duration-150"
              opacity={nodeOpacity}
              onclick={(e) => {
                e.stopPropagation();
                activeFocusDocId = node.id;
              }}
              ondblclick={(e) => {
                e.stopPropagation();
                onOpenDocument(node.doc, 1);
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
              <!-- Outer Accent Selection Aura -->
              {#if isFocus}
                <circle
                  r={node.radius + 7}
                  fill="none"
                  stroke={isDarkMode ? '#38bdf8' : '#0284c7'}
                  stroke-width="2.5"
                  opacity="0.95"
                  class="animate-pulse"
                />
              {:else if isHovered}
                <circle
                  r={node.radius + 5}
                  fill="none"
                  stroke={isDarkMode ? '#ffffff' : '#0f172a'}
                  stroke-width="1.8"
                  opacity="0.6"
                />
              {/if}

              <!-- External Accessible Distinction Ring -->
              {#if !node.isInternal}
                <circle
                  r={node.radius + 3.5}
                  fill="none"
                  stroke={isDarkMode ? '#a5b4fc' : '#6366f1'}
                  stroke-width="1.5"
                  stroke-dasharray="3 3"
                  opacity="0.8"
                />
              {/if}

              <!-- Node Body Circle -->
              <circle
                r={node.radius}
                fill={node.color}
                stroke={isFocus ? '#ffffff' : isDarkMode ? '#0f172a' : '#ffffff'}
                stroke-width={isFocus ? 2.5 : 1.8}
                style="filter: drop-shadow(0 2px 4px rgba(0,0,0,{isDarkMode ? '0.5' : '0.15'}));"
              />

              <!-- File Type Text inside Node -->
              <text
                text-anchor="middle"
                dy="3.5"
                font-size="9"
                font-family="monospace"
                font-weight="bold"
                fill="#ffffff"
                class="pointer-events-none tracking-tight uppercase"
              >
                {node.fileType.slice(0, 3)}
              </text>

              <!-- Node Label Below -->
              <g transform="translate(0, {node.radius + 12})">
                <rect
                  x={-Math.min(90, node.title.length * 3.4)}
                  y="-1"
                  width={Math.min(180, node.title.length * 6.8)}
                  height="16"
                  rx="4"
                  fill={isDarkMode ? '#0f172a' : '#ffffff'}
                  fill-opacity="0.88"
                  stroke={isFocus ? (isDarkMode ? '#38bdf8' : '#0284c7') : isDarkMode ? '#1e293b' : '#e2e8f0'}
                  stroke-width={isFocus ? 1.2 : 0.8}
                  class="pointer-events-none"
                />
                <text
                  text-anchor="middle"
                  dy="10"
                  font-size="9.5"
                  font-weight={isFocus ? '600' : '500'}
                  fill={isDarkMode ? (isFocus ? '#38bdf8' : '#e2e8f0') : (isFocus ? '#0284c7' : '#1e293b')}
                  class="pointer-events-none truncate"
                >
                  {node.title.length > 22 ? `${node.title.slice(0, 20)}...` : node.title}
                </text>

                <!-- Source Tag for External Docs -->
                {#if !node.isInternal}
                  <g transform="translate(0, 16)">
                    <rect
                      x="-40"
                      y="0"
                      width="80"
                      height="12"
                      rx="3"
                      fill={isDarkMode ? '#312e81' : '#e0e7ff'}
                      class="pointer-events-none"
                    />
                    <text
                      text-anchor="middle"
                      dy="9"
                      font-size="7.5"
                      font-weight="600"
                      fill={isDarkMode ? '#c7d2fe' : '#4338ca'}
                      class="pointer-events-none uppercase"
                    >
                      {node.collectionName.length > 12 ? `${node.collectionName.slice(0, 10)}..` : node.collectionName}
                    </text>
                  </g>
                {/if}
              </g>
            </g>
          {/each}
        </g>
      </svg>

      <!-- Edge Hover Tooltip -->
      {#if hoveredEdge}
        <div class="absolute top-4 left-4 z-20 pointer-events-none bg-white/95 dark:bg-neutral-900/95 border border-neutral-200 dark:border-neutral-800 rounded-lg p-3 shadow-lg max-w-xs text-xs backdrop-blur-md animate-in fade-in duration-150">
          <div class="flex items-center justify-between gap-2 text-[10px] font-mono text-neutral-400 mb-1">
            <span class="text-blue-600 dark:text-blue-400 font-semibold">{Math.round(hoveredEdge.weight * 100)}% Relationship Match</span>
            <span class="uppercase">{hoveredEdge.type}</span>
          </div>
          <div class="font-semibold text-neutral-800 dark:text-neutral-200 line-clamp-1">
            {hoveredEdge.srcTitle}
          </div>
          <div class="text-[10px] text-neutral-400 flex items-center gap-1 my-0.5">
            <span>connected to</span>
            <ArrowRight class="w-2.5 h-2.5" />
          </div>
          <div class="font-semibold text-neutral-800 dark:text-neutral-200 line-clamp-1 mb-1.5">
            {hoveredEdge.tgtTitle}
          </div>
          {#if hoveredEdge.reasons && hoveredEdge.reasons.length > 0}
            <div class="text-[10.5px] text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800/80 p-1.5 rounded border border-neutral-200 dark:border-neutral-700">
              {hoveredEdge.reasons[0]}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Bottom Canvas Legend & Zoom Controls -->
      <div class="absolute bottom-4 left-4 z-10 flex items-center gap-3 bg-white/90 dark:bg-neutral-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-2xs text-[11px]">
        <div class="flex items-center gap-1.5">
          <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
          <span class="text-neutral-600 dark:text-neutral-400 font-medium">In Collection</span>
        </div>
        {#if includeExternalDocs}
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full border border-dashed border-indigo-500 bg-indigo-500/20"></span>
            <span class="text-neutral-600 dark:text-neutral-400 font-medium">External Accessible</span>
          </div>
        {/if}
      </div>

      <!-- Zoom Floating Controls -->
      <div class="absolute bottom-4 right-4 z-10 flex items-center gap-1 bg-white/90 dark:bg-neutral-900/90 backdrop-blur-md p-1 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-2xs">
        <button
          type="button"
          onclick={() => (zoom = Math.min(2.8, zoom * 1.15))}
          class="p-1.5 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn class="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onclick={() => (zoom = Math.max(0.4, zoom * 0.85))}
          class="p-1.5 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut class="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onclick={resetViewport}
          class="p-1.5 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer"
          title="Reset View"
        >
          <RotateCcw class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- RIGHT INSPECTOR PANEL: FOCUSED DOCUMENT & RELATED DOCUMENTS -->
    <!-- ======================================================================= -->
    {#if isInspectorOpen}
      <div class="w-80 sm:w-96 bg-white dark:bg-neutral-900 border-l border-neutral-200 dark:border-neutral-800 flex flex-col shrink-0 overflow-hidden z-10 animate-in slide-in-from-right duration-200">
        <!-- Inspector Header -->
        <div class="p-3 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between gap-2 shrink-0">
          <div class="flex items-center gap-1.5 text-xs font-semibold text-neutral-900 dark:text-neutral-100">
            <Share2 class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span>Document Relationship Inspector</span>
          </div>
          <button
            type="button"
            onclick={() => (isInspectorOpen = false)}
            class="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200 cursor-pointer rounded"
          >
            <ChevronRight class="w-4 h-4" />
          </button>
        </div>

        <!-- Inspector Content -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {#if activeFocusDoc}
            <!-- Focus Card -->
            <div class="bg-neutral-50 dark:bg-neutral-800/60 p-4 rounded-xl border border-neutral-200 dark:border-neutral-700/80 space-y-2.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
                  {activeFocusNode?.isInternal ? 'In Current Collection' : `External: ${activeFocusNode?.collectionName}`}
                </span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-200/80 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-semibold uppercase">
                  {activeFocusDoc.fileType}
                </span>
              </div>

              <h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 leading-snug">
                {activeFocusDoc.title}
              </h2>

              <p class="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed line-clamp-3">
                {activeFocusDoc.summary}
              </p>

              <!-- Stats Pill Bar -->
              <div class="flex items-center gap-3 text-[11px] font-mono text-neutral-500 dark:text-neutral-400 pt-1">
                <span>{activeFocusDoc.pageCount} pages</span>
                <span>•</span>
                <span>{activeFocusDoc.chunkCount} chunks</span>
                <span>•</span>
                <span>{formatBytes(activeFocusDoc.sizeBytes)}</span>
              </div>

              <!-- Action Open Document -->
              <div class="pt-2 border-t border-neutral-200/80 dark:border-neutral-700/80 flex items-center justify-between">
                <button
                  type="button"
                  onclick={() => onOpenDocument(activeFocusDoc, 1)}
                  class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                >
                  <FileText class="w-3.5 h-3.5" />
                  <span>Open Full Document</span>
                  <ExternalLink class="w-3 h-3 ml-1" />
                </button>
              </div>
            </div>

            <!-- Entities / Topics Cloud -->
            {#if activeFocusDoc.entities && activeFocusDoc.entities.length > 0}
              <div>
                <span class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 block mb-1.5">
                  Semantic Entities & Concepts
                </span>
                <div class="flex flex-wrap gap-1">
                  {#each activeFocusDoc.entities as entity}
                    <span class="px-2 py-0.5 rounded text-[10.5px] bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
                      {entity}
                    </span>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Ranked Connected Documents List -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-[11px] font-semibold uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  Related Documents ({rankedRelatedDocs.length})
                </span>
                <span class="text-[10px] text-neutral-400 font-mono">Ranked by Vector Match</span>
              </div>

              {#if rankedRelatedDocs.length === 0}
                <div class="p-4 bg-neutral-50 dark:bg-neutral-800/40 rounded-lg border border-neutral-200 dark:border-neutral-800 text-center text-xs text-neutral-400">
                  No direct correlations above {Math.round(similarityThreshold * 100)}% threshold.
                  {#if !includeExternalDocs}
                    <button
                      type="button"
                      onclick={() => (includeExternalDocs = true)}
                      class="text-blue-600 dark:text-blue-400 hover:underline block mx-auto mt-1 cursor-pointer font-medium"
                    >
                      Search other accessible collections
                    </button>
                  {/if}
                </div>
              {:else}
                <div class="space-y-2">
                  {#each rankedRelatedDocs as item (item.node.id)}
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                      class="p-2.5 rounded-lg border transition-all cursor-pointer {
                        activeFocusDocId === item.node.id
                          ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-400 dark:border-blue-700 shadow-2xs'
                          : 'bg-white dark:bg-neutral-800/50 hover:bg-neutral-50 dark:hover:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
                      }"
                      onclick={() => (activeFocusDocId = item.node.id)}
                    >
                      <div class="flex items-center justify-between text-[11px] mb-1">
                        <div class="flex items-center gap-1.5">
                          <span
                            class="w-2 h-2 rounded-full"
                            style="background-color: {item.node.color}"
                          ></span>
                          <span class="font-semibold text-neutral-900 dark:text-neutral-100 truncate max-w-[170px]" title={item.node.title}>
                            {item.node.title}
                          </span>
                        </div>
                        <span class="font-mono font-bold text-blue-600 dark:text-blue-400 text-[10px]">
                          {item.similarity}% match
                        </span>
                      </div>

                      <!-- Similarity Match Progress Line -->
                      <div class="w-full h-1 bg-neutral-100 dark:bg-neutral-700 rounded-full overflow-hidden my-1.5">
                        <div
                          class="h-full bg-blue-500 rounded-full transition-all"
                          style="width: {item.similarity}%"
                        ></div>
                      </div>

                      <div class="flex items-center justify-between text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">
                        <span class="truncate max-w-[160px]">
                          {item.node.isInternal ? 'Current Collection' : item.node.collectionName}
                        </span>
                        <button
                          type="button"
                          onclick={(e) => {
                            e.stopPropagation();
                            onOpenDocument(item.node.doc, 1);
                          }}
                          class="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5 cursor-pointer"
                        >
                          <span>Read</span>
                          <ExternalLink class="w-2.5 h-2.5" />
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {:else}
            <div class="text-center py-12 text-neutral-400 text-xs">
              No document selected. Click any document node in the graph to inspect its relationships.
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>
