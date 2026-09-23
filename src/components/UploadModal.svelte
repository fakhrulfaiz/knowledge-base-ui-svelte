<script lang="ts">
  import {
    X,
    Upload,
    Layers,
    ArrowRight
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, IngestionConfig } from '../types';
  import { chunkTextIntoPages } from '../utils/chunker';

  interface Props {
    collection: Collection;
    ingestionConfig?: IngestionConfig;
    onClose: () => void;
    onUploadComplete: (newDoc: DocumentItem) => boolean | void;
  }

  let {
    collection,
    ingestionConfig,
    onClose,
    onUploadComplete,
  }: Props = $props();

  const SAMPLE_PRESETS = [
    {
      title: 'eBPF Kernel Telemetry & Network Flow Observability RFC',
      filename: 'INFRA-eBPF-Network-Flow-Observability.md',
      fileType: 'md' as const,
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
        }
      ]
    }
  ];

  let selectedPresetIndex = $state<number>(0);
  let docTitle = $state(SAMPLE_PRESETS[0].title);
  let filename = $state(SAMPLE_PRESETS[0].filename);
  let fileType = $state<'pdf' | 'docx' | 'md' | 'report'>('md');
  let isProcessing = $state(false);
  let stepMessage = $state('');

  function handleSelectPreset(idx: number) {
    selectedPresetIndex = idx;
    const p = SAMPLE_PRESETS[idx];
    docTitle = p.title;
    filename = p.filename;
    fileType = p.fileType;
  }

  async function handleIngest() {
    isProcessing = true;
    stepMessage = 'Reading document pages...';
    await new Promise((r) => setTimeout(r, 350));

    stepMessage = 'Extracting readable sections and passages...';
    await new Promise((r) => setTimeout(r, 400));

    stepMessage = 'Adding to collection index...';
    await new Promise((r) => setTimeout(r, 350));

    const currentPreset = SAMPLE_PRESETS[selectedPresetIndex];
    const docId = `doc-${Date.now()}`;
    const pages = chunkTextIntoPages(
      docId,
      collection.id,
      collection.scope,
      currentPreset.pages,
      ingestionConfig
    );
    const totalChunks = pages.reduce((acc, p) => acc + p.chunks.length, 0);

    const newDoc: DocumentItem = {
      id: docId,
      collectionId: collection.id,
      title: docTitle,
      filename,
      fileType,
      source: 'upload',
      uploadedAt: new Date().toISOString(),
      uploadedBy: 'Elena Rostova',
      sizeBytes: 1350000,
      pageCount: pages.length,
      chunkCount: totalChunks,
      summary: currentPreset.summary,
      entities: ['eBPF', 'Kubernetes', 'AES-256-GCM', 'Secret Manager', 'Prometheus'],
      crossReferences: [],
      semanticTopics: ['Infrastructure', 'Security', 'Telemetry'],
      pages,
    };

    const success = onUploadComplete(newDoc);
    isProcessing = false;
    if (success !== false) {
      onClose();
    }
  }
</script>

<div class="fixed inset-0 z-50 bg-neutral-900/80 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150 select-none">
  <div class="w-full max-w-2xl bg-white dark:bg-neutral-900 rounded-xl shadow-2xl flex flex-col overflow-hidden border border-neutral-300 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100">
    <!-- Header -->
    <div class="h-14 px-6 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="p-1.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
          <Upload class="w-4 h-4" />
        </div>
        <div>
          <h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Direct Document Upload &amp; Ingestion
          </h2>
          <div class="text-[11px] text-neutral-400 dark:text-neutral-500">
            Target Collection: <strong class="text-neutral-700 dark:text-neutral-300">{collection.name}</strong>
          </div>
        </div>
      </div>

      <button
        type="button"
        onclick={onClose}
        class="p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 rounded transition-colors cursor-pointer"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Processing State Overlay -->
    {#if isProcessing}
      <div class="absolute inset-0 z-20 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center">
        <div class="w-12 h-12 rounded-full border-3 border-neutral-200 dark:border-neutral-700 border-t-neutral-900 dark:border-t-neutral-100 animate-spin mb-4"></div>
        <h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          Extracting &amp; Chunking Document
        </h3>
        <p class="text-xs text-neutral-500 dark:text-neutral-400 font-mono mt-1 max-w-md">
          {stepMessage}
        </p>
      </div>
    {/if}

    <!-- Form Body -->
    <div class="p-6 space-y-4 overflow-y-auto text-xs">
      <!-- Preset Selectors -->
      <div>
        <span class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1.5">
          Select Enterprise Document Template or Upload File:
        </span>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {#each SAMPLE_PRESETS as preset, idx (idx)}
            <div
              role="button"
              tabindex="0"
              onclick={() => handleSelectPreset(idx)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleSelectPreset(idx); }}
              class="p-3 rounded-lg border cursor-pointer transition-all {selectedPresetIndex === idx
                ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                : 'bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200'}"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="font-mono text-[10px] uppercase opacity-75">
                  {preset.fileType}
                </span>
                <span class="text-[10px] opacity-60">
                  {preset.pages.length} pages
                </span>
              </div>
              <div class="font-semibold text-xs line-clamp-1">
                {preset.title}
              </div>
              <p class="text-[11px] mt-1 line-clamp-2 {selectedPresetIndex === idx ? 'text-blue-100' : 'text-neutral-500 dark:text-neutral-400'}">
                {preset.summary}
              </p>
            </div>
          {/each}
        </div>
      </div>

      <!-- Document Metadata Inputs -->
      <div class="space-y-3 pt-2 border-t border-neutral-100 dark:border-neutral-800">
        <div>
          <label for="up-title" class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1">
            Document Title
          </label>
          <input
            id="up-title"
            type="text"
            bind:value={docTitle}
            class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="up-fn" class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1">
              Filename
            </label>
            <input
              id="up-fn"
              type="text"
              bind:value={filename}
              class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 font-mono focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500"
            />
          </div>
          <div>
            <label for="up-fmt" class="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 block mb-1">
              Format
            </label>
            <select
              id="up-fmt"
              bind:value={fileType}
              class="w-full px-3 py-2 bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md text-xs text-neutral-900 dark:text-neutral-100 focus:outline-hidden focus:border-neutral-400 dark:focus:border-neutral-500"
            >
              <option value="pdf" class="dark:bg-neutral-800">PDF Document (.pdf)</option>
              <option value="docx" class="dark:bg-neutral-800">Word Document (.docx)</option>
              <option value="md" class="dark:bg-neutral-800">Markdown (.md)</option>
              <option value="report" class="dark:bg-neutral-800">Engineering Report (.report)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Chunking Pipeline Specs Preview -->
      <div class="p-3 bg-neutral-100 dark:bg-neutral-800/60 rounded-lg border border-neutral-200 dark:border-neutral-700 text-[11px] text-neutral-600 dark:text-neutral-300 space-y-1 font-mono">
        <div class="font-semibold text-neutral-800 dark:text-neutral-200 font-sans flex items-center gap-1.5">
          <Layers class="w-3.5 h-3.5 text-neutral-500 dark:text-neutral-400" />
          <span>Chunking Pipeline Parameters:</span>
        </div>
        <div class="flex justify-between">
          <span>Token Chunk Target:</span>
          <span class="text-neutral-900 dark:text-neutral-100 font-semibold">150–220 tokens</span>
        </div>
        <div class="flex justify-between">
          <span>Overlap Window:</span>
          <span class="text-neutral-900 dark:text-neutral-100 font-semibold">25 tokens</span>
        </div>
        <div class="flex justify-between">
          <span>Deep-Link Offset Preservation:</span>
          <span class="text-emerald-700 dark:text-emerald-400 font-semibold">Enabled (Character Span Mapping)</span>
        </div>
        <div class="flex justify-between pt-1 border-t border-neutral-200 dark:border-neutral-700">
          <span>Collection Storage Quota:</span>
          <span class="text-blue-700 dark:text-blue-400 font-semibold">{collection.allocatedGb || 10} GB ({collection.scope === 'team' ? 'Team Allocated' : collection.scope === 'mine' ? 'Personal Cap' : 'Org Pool'})</span>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="h-14 px-6 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
      <div class="text-xs text-neutral-400 dark:text-neutral-500">
        Estimated ~6 chunks will be created
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={onClose}
          class="px-3 py-1.5 text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 font-medium cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="button"
          onclick={handleIngest}
          disabled={isProcessing || !docTitle.trim()}
          class="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer"
        >
          <span>Extract &amp; Ingest</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </div>
</div>
