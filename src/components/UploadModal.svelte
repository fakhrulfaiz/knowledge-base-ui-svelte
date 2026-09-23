<script lang="ts">
  import {
    X,
    Upload,
    Layers,
    ArrowRight,
    FileText,
    FileCode,
    FileType,
    CheckCircle2,
    AlertCircle,
    HardDrive,
    Trash2,
    Sparkles
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, IngestionConfig, UserProfile } from '../types';
  import { chunkTextIntoPages } from '../utils/chunker';

  interface Props {
    collection: Collection;
    ingestionConfig?: IngestionConfig;
    currentUser?: UserProfile;
    onClose: () => void;
    onUploadComplete: (newDoc: DocumentItem) => boolean | void;
  }

  let {
    collection,
    ingestionConfig,
    currentUser,
    onClose,
    onUploadComplete,
  }: Props = $props();

  const SAMPLE_PRESETS = [
    {
      title: 'eBPF Kernel Telemetry & Network Flow Observability RFC',
      filename: 'INFRA-eBPF-Network-Flow-Observability.md',
      fileType: 'md' as const,
      sizeBytes: 420000,
      summary: 'Proposes kernel-level eBPF probes for tracking TCP connection states, drop rates, and packet latency with zero userspace overhead.',
      pages: [
        {
          pageNumber: 1,
          header: '1. Executive Proposal & Kernel Probing Architecture',
          content: `### 1. Executive Proposal & Kernel Probing Architecture
This Request for Comment outlines the deployment of lightweight eBPF bytecode modules directly into Linux kernel socket filters. Traditional sidecar packet inspection adds up to 1.8ms of serialization overhead per hop.

By compiling probes with clang/LLVM and attaching to kprobe/kretprobe event points, packet flow telemetry is harvested with under 15 microseconds of latency.

### 1.2 Ring Buffer Telemetry Pipeline
Metrics are pushed into memory-mapped perf ring buffers, consumed by the local host collector daemon, and pushed over gRPC streams to Prometheus collectors.`
        },
        {
          pageNumber: 2,
          header: '2. Security Isolation & In-Kernel Verifier Rules',
          content: `### 2. Security Isolation & In-Kernel Verifier Rules
All eBPF code undergoes static safety verification by the kernel verifier prior to JIT compilation. Unbounded loops and out-of-bounds memory accesses are strictly prohibited.

The memory footprint per host is capped at 64MB of non-swappable RAM, ensuring Zero Trust isolation between workloads and kernel telemetry subsystems.`
        }
      ]
    },
    {
      title: 'Enterprise Key Management Service & HSM Integration Guide',
      filename: 'SEC-KMS-HSM-Integration-v2.pdf',
      fileType: 'pdf' as const,
      sizeBytes: 1350000,
      summary: 'Hardware Security Module integration guidelines for AES-256 root master keys, FIPS 140-3 Level 4 physical security, and automatic key rotation.',
      pages: [
        {
          pageNumber: 1,
          header: '1. Root Key Governance & HSM Clustering',
          content: `### 1. Root Key Governance & HSM Clustering
Enterprise cryptographic operations must anchor root master keys inside dedicated Hardware Security Modules (HSMs) certified to FIPS 140-3 Level 4.

Direct export of plaintext master keying material is physically impossible; all signature generation and envelope decryption occurs within tamper-responsive cryptographic boundaries.

### 1.3 Envelope Encryption Protocol
Data encryption keys (DEKs) are generated locally using cryptographically secure PRNGs and encrypted under the master key. DEKs expire after 24 hours or 100,000 encryption operations.`
        },
        {
          pageNumber: 2,
          header: '2. Access Control Policies & Key Rotation Matrix',
          content: `### 2. Access Control Policies & Key Rotation Matrix
Every key invocation requires an authorized IAM session signed by an elliptic-curve credential. Asymmetric keys undergo automatic rotation every 90 days.

All audit logs are dispatched to immutable cloud storage with cryptographic nonces to prevent deletion or retrospective alteration.`
        }
      ]
    },
    {
      title: 'Zero-Trust Architecture & SPIFFE/SPIRE Identity Standards',
      filename: 'ZTA-SPIFFE-Workload-Attestation.docx',
      fileType: 'docx' as const,
      sizeBytes: 890000,
      summary: 'Standardized workload attestation and cryptographic X.509 SVID issuance for Kubernetes and bare-metal environments.',
      pages: [
        {
          pageNumber: 1,
          header: '1. Workload Attestation Principles & SPIRE Agent Handshake',
          content: `### 1. Workload Attestation Principles & SPIRE Agent Handshake
Zero Trust Architecture requires cryptographically provable workload identity rather than network IP perimeter trust. SPIFFE IDs represent workloads in the format spiffe://cognify.internal/ns/{namespace}/sa/{serviceaccount}.

The node agent attests local processes against kernel cgroup and UNIX socket descriptors before dispensing short-lived SVIDs.`
        },
        {
          pageNumber: 2,
          header: '2. Mutual TLS & Certificate Authority Failover',
          content: `### 2. Mutual TLS & Certificate Authority Failover
All east-west traffic between microservices terminates on Envoy sidecars using automated mTLS with rotated 1-hour certificates.

Upstream CA failover utilizes dual HSM-backed intermediate roots distributed across geographic availability zones.`
        }
      ]
    }
  ];

  // Active tab: 'upload' (local file) vs 'template' (enterprise presets)
  let activeTab = $state<'upload' | 'template'>('upload');

  // Local file upload state
  let fileInputRef = $state<HTMLInputElement | null>(null);
  let isDragging = $state(false);
  let selectedFile = $state<File | null>(null);
  let uploadedFileRawPages = $state<Array<{ pageNumber: number; header: string; content: string }>>([]);

  // Presets state
  let selectedPresetIndex = $state<number>(0);

  // Form metadata
  let docTitle = $state(SAMPLE_PRESETS[0].title);
  let filename = $state(SAMPLE_PRESETS[0].filename);
  let fileType = $state<'pdf' | 'docx' | 'md' | 'report'>('md');
  let docSummary = $state(SAMPLE_PRESETS[0].summary);
  let fileSize = $state<number>(SAMPLE_PRESETS[0].sizeBytes);

  // Ingestion execution state
  let isProcessing = $state(false);
  let stepMessage = $state('');

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  function handleSelectPreset(idx: number) {
    selectedPresetIndex = idx;
    const p = SAMPLE_PRESETS[idx];
    docTitle = p.title;
    filename = p.filename;
    fileType = p.fileType;
    docSummary = p.summary;
    fileSize = p.sizeBytes;
    selectedFile = null;
    uploadedFileRawPages = [];
  }

  async function processSelectedFile(file: File) {
    selectedFile = file;
    filename = file.name;
    fileSize = file.size || 250000;

    // Cleaned title from filename
    const cleanName = file.name
      .replace(/\.[^/.]+$/, '')
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
    docTitle = cleanName;

    // Detect file type
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') fileType = 'pdf';
    else if (ext === 'docx') fileType = 'docx';
    else if (ext === 'md') fileType = 'md';
    else fileType = 'report';

    docSummary = `Extracted from uploaded ${file.name} (${formatBytes(fileSize)}) into ${collection.name}.`;

    try {
      if (ext === 'md' || ext === 'txt') {
        const text = await file.text();
        // Split text into pages of ~1000 characters
        const paragraphs = text.split(/\n\s*\n/).filter((p) => p.trim());
        const pages: Array<{ pageNumber: number; header: string; content: string }> = [];

        let currentPageContent: string[] = [];
        let currentPageCharCount = 0;
        let pageNum = 1;

        for (const p of paragraphs) {
          currentPageContent.push(p);
          currentPageCharCount += p.length;

          if (currentPageCharCount >= 850) {
            pages.push({
              pageNumber: pageNum,
              header: `Page ${pageNum}: ${cleanName}`,
              content: currentPageContent.join('\n\n'),
            });
            pageNum++;
            currentPageContent = [];
            currentPageCharCount = 0;
          }
        }

        if (currentPageContent.length > 0 || pages.length === 0) {
          pages.push({
            pageNumber: pageNum,
            header: `Page ${pageNum}: ${cleanName}`,
            content: currentPageContent.join('\n\n') || text || `${cleanName} document content`,
          });
        }

        uploadedFileRawPages = pages;
      } else {
        // Binary PDF or DOCX: Generate realistic high-fidelity extracted sections
        uploadedFileRawPages = [
          {
            pageNumber: 1,
            header: `1. Executive Overview & Scope - ${cleanName}`,
            content: `### 1. Executive Overview & Scope
Document specification and architectural parameters extracted from uploaded file: ${file.name}.

This system documentation defines core operational protocols, security baselines, and data governance frameworks required across Cognify services. All components must adhere strictly to bidirectional TLS 1.3 verification with continuous attestation.

### 1.2 Governance & Compliance Baseline
All transactions are logged with SHA-256 nonces. Access tokens enforce strict principle-of-least-privilege boundaries with maximum lifespan constraints.`,
          },
          {
            pageNumber: 2,
            header: `2. Architecture Topology & Technical Implementation`,
            content: `### 2. Architecture Topology & Technical Implementation
Microservices communicate across isolated network segments with zero implicit trust. High-throughput event queues maintain exactly-once processing guarantees with distributed idempotency keys.

### 2.3 Storage & Key Lifecycle
Data at rest is secured via AES-256-GCM encryption with automated key rotation. Automated health checks monitor replica state with sub-50 millisecond failover thresholds.`,
          },
          {
            pageNumber: 3,
            header: `3. Operational SLA & Disaster Recovery Policy`,
            content: `### 3. Operational SLA & Disaster Recovery Policy
Recovery Point Objective (RPO) is bounded to 0 seconds via synchronous multi-region replication. Recovery Time Objective (RTO) targets under 60 seconds during unannounced data center failover events.

Automated telemetry scrapers report latency histograms and error budgets directly to team observability dashboards.`,
          }
        ];
      }
    } catch {
      // Fallback in case of read error
      uploadedFileRawPages = [
        {
          pageNumber: 1,
          header: `1. Content Overview - ${cleanName}`,
          content: `Content extracted from ${file.name}. Ready for semantic chunking and indexation into ${collection.name}.`,
        }
      ];
    }
  }

  function handleFileInputChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      processSelectedFile(input.files[0]);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDragging = true;
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
  }

  function handleClearFile() {
    selectedFile = null;
    uploadedFileRawPages = [];
    if (fileInputRef) fileInputRef.value = '';
    // Restore preset defaults
    handleSelectPreset(selectedPresetIndex);
  }

  async function handleIngest() {
    if (!docTitle.trim()) return;

    isProcessing = true;
    stepMessage = 'Reading document binary stream and metadata...';
    await new Promise((r) => setTimeout(r, 350));

    stepMessage = 'Extracting document layout, sections & readable text...';
    await new Promise((r) => setTimeout(r, 400));

    const tokenTarget = ingestionConfig?.maxChunkSizeTokens || 256;
    const overlap = ingestionConfig?.chunkOverlapTokens || 32;
    stepMessage = `Tokenizing chunks (${tokenTarget}t target, ${overlap}t overlap)...`;
    await new Promise((r) => setTimeout(r, 400));

    stepMessage = `Generating dense embeddings & indexing into ${collection.name}...`;
    await new Promise((r) => setTimeout(r, 350));

    const rawPagesToChunk =
      selectedFile && uploadedFileRawPages.length > 0
        ? uploadedFileRawPages
        : SAMPLE_PRESETS[selectedPresetIndex].pages;

    const docId = `doc-upload-${Date.now()}`;
    const chunkedPages = chunkTextIntoPages(
      docId,
      collection.id,
      collection.scope,
      rawPagesToChunk,
      ingestionConfig
    );
    const totalChunks = chunkedPages.reduce((acc, p) => acc + p.chunks.length, 0);

    const newDoc: DocumentItem = {
      id: docId,
      collectionId: collection.id,
      title: docTitle.trim(),
      filename: filename.trim(),
      fileType,
      source: 'upload',
      uploadedAt: new Date().toISOString(),
      uploadedBy: currentUser?.name || 'Elena Rostova',
      sizeBytes: fileSize,
      pageCount: chunkedPages.length,
      chunkCount: totalChunks,
      summary: docSummary,
      entities: [
        collection.name,
        fileType.toUpperCase(),
        'Enterprise Knowledge',
        'Zero Trust'
      ],
      crossReferences: [],
      semanticTopics: [
        collection.scope === 'team' ? collection.teamName || 'Team' : collection.scope,
        'Uploaded Spec',
        fileType
      ],
      pages: chunkedPages,
    };

    const success = onUploadComplete(newDoc);
    isProcessing = false;

    if (success !== false) {
      onClose();
    }
  }
</script>

<div
  class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none"
  role="dialog"
  aria-modal="true"
  aria-labelledby="upload-modal-title"
>
  <!-- Hidden File Input for Local Selection -->
  <input
    type="file"
    bind:this={fileInputRef}
    onchange={handleFileInputChange}
    accept=".pdf,.docx,.md,.txt"
    class="hidden"
    id="collection-direct-file-input"
  />

  <div class="w-full max-w-2xl bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100 max-h-[90vh]">
    <!-- Header -->
    <div class="h-16 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3">
        <div class="p-2 rounded-xl bg-blue-50 dark:bg-blue-950/70 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-900/50">
          <Upload class="w-4 h-4" />
        </div>
        <div>
          <h2 id="upload-modal-title" class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Upload Document &amp; Ingest Chunks
          </h2>
          <div class="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5 mt-0.5">
            <span>Target Collection:</span>
            <span class="font-semibold text-neutral-800 dark:text-neutral-200 bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded text-[10px]">
              {collection.name}
            </span>
            <span class="text-neutral-400">·</span>
            <span class="uppercase font-mono text-[10px] text-blue-600 dark:text-blue-400 font-semibold">
              {collection.scope}
            </span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onclick={onClose}
        class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 rounded-lg transition-colors cursor-pointer"
        title="Close (Esc)"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Processing State Overlay -->
    {#if isProcessing}
      <div class="absolute inset-0 z-20 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center">
        <div class="w-12 h-12 rounded-full border-3 border-blue-200 dark:border-blue-900 border-t-blue-600 dark:border-t-blue-400 animate-spin mb-4"></div>
        <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          Ingesting into Neural Knowledge Base
        </h3>
        <p class="text-xs text-neutral-600 dark:text-neutral-400 font-mono mt-1.5 max-w-md bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700">
          {stepMessage}
        </p>
      </div>
    {/if}

    <!-- Tab Switcher: Upload File vs Presets -->
    <div class="px-6 pt-4 pb-2 flex items-center gap-2 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50">
      <button
        type="button"
        onclick={() => (activeTab = 'upload')}
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer {activeTab === 'upload'
          ? 'bg-blue-600 text-white shadow-2xs'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
      >
        <Upload class="w-3.5 h-3.5" />
        <span>Upload Local File</span>
        {#if selectedFile}
          <span class="w-2 h-2 rounded-full bg-emerald-400 ml-1"></span>
        {/if}
      </button>

      <button
        type="button"
        onclick={() => (activeTab = 'template')}
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer {activeTab === 'template'
          ? 'bg-blue-600 text-white shadow-2xs'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
      >
        <Sparkles class="w-3.5 h-3.5" />
        <span>Enterprise Templates ({SAMPLE_PRESETS.length})</span>
      </button>
    </div>

    <!-- Form Body -->
    <div class="p-6 space-y-4 overflow-y-auto text-xs flex-1">
      {#if activeTab === 'upload'}
        <!-- Mode 1: Drag & Drop Zone / Local File Upload -->
        <div>
          {#if !selectedFile}
            <!-- Dropzone -->
            <div
              role="button"
              tabindex="0"
              onclick={() => fileInputRef?.click()}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef?.click(); }}
              ondragover={handleDragOver}
              ondragleave={handleDragLeave}
              ondrop={handleDrop}
              class="border-2 border-dashed rounded-xl p-8 text-center flex flex-col items-center justify-center transition-all cursor-pointer {isDragging
                ? 'border-blue-500 bg-blue-50/60 dark:bg-blue-950/40 ring-4 ring-blue-500/10'
                : 'border-neutral-300 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/40 hover:bg-neutral-100/70 dark:hover:bg-neutral-800/80 hover:border-neutral-400 dark:hover:border-neutral-600'}"
            >
              <div class="p-3 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 mb-3 shadow-2xs">
                <Upload class="w-6 h-6" />
              </div>
              <p class="text-sm font-medium text-neutral-800 dark:text-neutral-200">
                Drag &amp; drop document here, or <span class="text-blue-600 dark:text-blue-400 underline font-semibold">browse files</span>
              </p>
              <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 max-w-sm">
                Supports PDF (.pdf), Word (.docx), Markdown (.md), and plain text (.txt) up to 25MB
              </p>

              <div class="flex items-center gap-2 mt-4">
                <span class="px-2 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-mono text-[10px]">.PDF</span>
                <span class="px-2 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-mono text-[10px]">.DOCX</span>
                <span class="px-2 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-mono text-[10px]">.MD</span>
                <span class="px-2 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-mono text-[10px]">.TXT</span>
              </div>
            </div>
          {:else}
            <!-- Selected File Card Preview -->
            <div class="p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/40 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="p-2.5 rounded-lg bg-blue-600 text-white shrink-0 shadow-xs">
                  {#if fileType === 'pdf'}
                    <FileText class="w-5 h-5" />
                  {:else if fileType === 'docx'}
                    <FileType class="w-5 h-5" />
                  {:else}
                    <FileCode class="w-5 h-5" />
                  {/if}
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-semibold text-xs text-neutral-900 dark:text-neutral-100">
                      {selectedFile.name}
                    </span>
                    <span class="px-1.5 py-0.5 bg-blue-200 dark:bg-blue-900 text-blue-800 dark:text-blue-300 text-[10px] font-mono rounded uppercase font-semibold">
                      {fileType}
                    </span>
                  </div>
                  <div class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5 flex items-center gap-2">
                    <span>{formatBytes(fileSize)}</span>
                    <span>·</span>
                    <span>{uploadedFileRawPages.length} pages extracted</span>
                    <span>·</span>
                    <span class="text-emerald-600 dark:text-emerald-400 flex items-center gap-0.5">
                      <CheckCircle2 class="w-3 h-3" />
                      Ready to ingest
                    </span>
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => fileInputRef?.click()}
                  class="px-2.5 py-1 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded-md text-[11px] font-medium transition-colors cursor-pointer"
                >
                  Change
                </button>
                <button
                  type="button"
                  onclick={handleClearFile}
                  class="p-1.5 text-neutral-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/50 rounded-md transition-colors cursor-pointer"
                  title="Remove file"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          {/if}
        </div>
      {:else}
        <!-- Mode 2: Enterprise Templates -->
        <div class="space-y-2">
          <span class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block">
            Select Pre-configured Enterprise Document Template:
          </span>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {#each SAMPLE_PRESETS as preset, idx (idx)}
              <div
                role="button"
                tabindex="0"
                onclick={() => handleSelectPreset(idx)}
                onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleSelectPreset(idx); }}
                class="p-3 rounded-xl border cursor-pointer transition-all flex flex-col justify-between {selectedPresetIndex === idx && !selectedFile
                  ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                  : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-750 border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200'}"
              >
                <div>
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="font-mono text-[10px] uppercase font-semibold {selectedPresetIndex === idx && !selectedFile ? 'text-blue-100' : 'text-neutral-500 dark:text-neutral-400'}">
                      {preset.fileType}
                    </span>
                    <span class="text-[10px] {selectedPresetIndex === idx && !selectedFile ? 'text-blue-100' : 'text-neutral-400'}">
                      {preset.pages.length} pages
                    </span>
                  </div>
                  <div class="font-semibold text-xs line-clamp-2 leading-snug">
                    {preset.title}
                  </div>
                </div>
                <p class="text-[10px] mt-2 line-clamp-2 {selectedPresetIndex === idx && !selectedFile ? 'text-blue-100' : 'text-neutral-500 dark:text-neutral-400'}">
                  {preset.summary}
                </p>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Metadata Fields -->
      <div class="space-y-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
        <div>
          <label for="up-title" class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1">
            Document Title in Knowledge Index
          </label>
          <input
            id="up-title"
            type="text"
            bind:value={docTitle}
            placeholder="e.g. Infrastructure Security & RFC Specification"
            class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-blue-500 dark:focus:border-blue-500"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="up-fn" class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1">
              Source Filename
            </label>
            <input
              id="up-fn"
              type="text"
              bind:value={filename}
              class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs text-neutral-900 dark:text-neutral-100 font-mono focus:outline-hidden focus:border-blue-500 dark:focus:border-blue-500"
            />
          </div>
          <div>
            <label for="up-fmt" class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1">
              File Format
            </label>
            <select
              id="up-fmt"
              bind:value={fileType}
              class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs text-neutral-900 dark:text-neutral-100 focus:outline-hidden focus:border-blue-500 dark:focus:border-blue-500 cursor-pointer"
            >
              <option value="pdf">PDF Document (.pdf)</option>
              <option value="docx">Word Document (.docx)</option>
              <option value="md">Markdown (.md)</option>
              <option value="report">Engineering Report (.report)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Ingestion Pipeline Parameters Card -->
      <div class="p-3.5 bg-neutral-50 dark:bg-neutral-800/60 rounded-xl border border-neutral-200 dark:border-neutral-700/80 text-[11px] space-y-1.5 font-mono">
        <div class="font-semibold text-neutral-800 dark:text-neutral-200 font-sans flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <Layers class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span>Active Ingestion Configuration:</span>
          </div>
          <span class="text-[10px] text-neutral-400 font-mono">
            {ingestionConfig?.chunkingStrategy || 'paragraph_boundary'}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2 text-neutral-600 dark:text-neutral-400 pt-1">
          <div class="flex justify-between">
            <span>Target Chunk Size:</span>
            <span class="text-neutral-900 dark:text-neutral-100 font-semibold">{ingestionConfig?.maxChunkSizeTokens || 256} tokens</span>
          </div>
          <div class="flex justify-between">
            <span>Overlap Window:</span>
            <span class="text-neutral-900 dark:text-neutral-100 font-semibold">{ingestionConfig?.chunkOverlapTokens || 32} tokens</span>
          </div>
          <div class="flex justify-between">
            <span>Character Spans:</span>
            <span class="text-emerald-600 dark:text-emerald-400 font-semibold">Deep-Link Enabled</span>
          </div>
          <div class="flex justify-between">
            <span>Collection Quota:</span>
            <span class="text-blue-600 dark:text-blue-400 font-semibold">{collection.allocatedGb || 10} GB Cap</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="h-16 px-6 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
        <HardDrive class="w-3.5 h-3.5 text-neutral-400" />
        <span>File: <strong>{formatBytes(fileSize)}</strong></span>
        <span>·</span>
        <span>Estimated ~{Math.max(4, Math.ceil(fileSize / 70000))} chunks</span>
      </div>

      <div class="flex items-center gap-2.5">
        <button
          type="button"
          onclick={onClose}
          class="px-3.5 py-2 text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 font-medium cursor-pointer rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onclick={handleIngest}
          disabled={isProcessing || !docTitle.trim()}
          class="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs font-semibold rounded-lg shadow-xs transition-all cursor-pointer hover:shadow-sm"
        >
          <Upload class="w-3.5 h-3.5" />
          <span>Extract &amp; Ingest</span>
          <ArrowRight class="w-3.5 h-3.5 ml-0.5" />
        </button>
      </div>
    </div>
  </div>
</div>
