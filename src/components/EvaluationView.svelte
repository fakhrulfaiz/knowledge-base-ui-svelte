<script lang="ts">
  import {
    Activity,
    CheckCircle2,
    AlertTriangle,
    Clock,
    Play,
    RefreshCw,
    Sliders,
    Search,
    Filter,
    Layers,
    Sparkles,
    Check,
    X,
    ChevronDown,
    ArrowUpRight,
    ShieldCheck,
    Gauge,
    Database
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, EvalMetric, EvalTestCase } from '../types';
  import { INITIAL_EVAL_METRICS, INITIAL_EVAL_TEST_CASES } from '../data/chatAndEvalData';

  interface Props {
    collections: Collection[];
    documents: DocumentItem[];
  }

  let { collections, documents }: Props = $props();

  let metrics = $state<EvalMetric[]>(INITIAL_EVAL_METRICS);
  let testCases = $state<EvalTestCase[]>(INITIAL_EVAL_TEST_CASES);
  let isRunningBenchmark = $state(false);
  let filterStatus = $state<'all' | 'passed' | 'review' | 'failed'>('all');
  let searchQuery = $state('');
  let selectedTestCase = $state<EvalTestCase | null>(null);

  // Tunable simulation parameters
  let topK = $state(5);
  let minScore = $state(0.75);
  let enableReranker = $state(true);

  let filteredTestCases = $derived(
    testCases.filter((tc) => {
      if (filterStatus !== 'all' && tc.status !== filterStatus) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          tc.query.toLowerCase().includes(q) ||
          tc.targetCollection.toLowerCase().includes(q) ||
          tc.expectedSource.toLowerCase().includes(q)
        );
      }
      return true;
    })
  );

  let passedCount = $derived(testCases.filter((tc) => tc.status === 'passed').length);
  let reviewCount = $derived(testCases.filter((tc) => tc.status === 'review').length);
  let overallPassRate = $derived(
    testCases.length > 0 ? Math.round((passedCount / testCases.length) * 100) : 100
  );

  function runBenchmark() {
    isRunningBenchmark = true;
    setTimeout(() => {
      // Simulate live evaluation across Milvus collections
      testCases = testCases.map((tc) => {
        const bonus = enableReranker ? 2 : -4;
        const newContext = Math.min(100, Math.max(70, tc.contextRelevance + Math.floor(Math.random() * 5 - 2) + bonus));
        const newGrounded = Math.min(100, Math.max(75, tc.groundedness + Math.floor(Math.random() * 4 - 1)));
        const newAns = Math.min(100, Math.max(70, tc.answerRelevance + Math.floor(Math.random() * 4 - 2)));
        const newLatency = Math.max(18, tc.latencyMs + Math.floor(Math.random() * 8 - 4) + (enableReranker ? 12 : 0));
        const isPass = newContext >= 85 && newGrounded >= 90;

        return {
          ...tc,
          contextRelevance: newContext,
          groundedness: newGrounded,
          answerRelevance: newAns,
          latencyMs: newLatency,
          status: isPass ? 'passed' : 'review'
        };
      });

      // Update metrics
      metrics = [
        {
          name: 'Context Relevance',
          score: Number((testCases.reduce((a, b) => a + b.contextRelevance, 0) / testCases.length).toFixed(1)),
          change: enableReranker ? '+2.8%' : '-1.5%',
          status: 'optimal',
          description: 'Proportion of retrieved chunks directly contributing to the answer without noise.'
        },
        {
          name: 'Groundedness / Faithfulness',
          score: Number((testCases.reduce((a, b) => a + b.groundedness, 0) / testCases.length).toFixed(1)),
          change: '+0.4%',
          status: 'optimal',
          description: 'Verification that all statements are strictly supported by retrieved vector chunks.'
        },
        {
          name: 'Answer Relevance',
          score: Number((testCases.reduce((a, b) => a + b.answerRelevance, 0) / testCases.length).toFixed(1)),
          change: '+1.1%',
          status: 'optimal',
          description: 'Degree to which the generated synthesis directly addresses user intent.'
        },
        {
          name: 'Milvus P95 Latency',
          score: Math.max(...testCases.map((t) => t.latencyMs)),
          change: enableReranker ? '+8ms' : '-4ms',
          status: 'optimal',
          description: 'HNSW vector search query response time across 1,247 chunks.'
        }
      ];

      isRunningBenchmark = false;
    }, 850);
  }
</script>

<div class="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Header Bar -->
  <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-3">
      <div class="p-1.5 rounded-lg bg-emerald-600/10 text-emerald-600 dark:text-emerald-400">
        <Activity class="w-4.5 h-4.5" />
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-sm font-bold text-neutral-900 dark:text-neutral-100">
            RAG Triad &amp; Retrieval Evaluation
          </h1>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300">
            {overallPassRate}% Passed
          </span>
        </div>
        <p class="text-[11px] text-neutral-400 font-mono">
          Continuous quality assurance for Milvus embeddings and hallucination drift
        </p>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-2.5">
      <button
        type="button"
        onclick={runBenchmark}
        disabled={isRunningBenchmark}
        class="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
      >
        {#if isRunningBenchmark}
          <RefreshCw class="w-3.5 h-3.5 animate-spin" />
          <span>Evaluating Suite...</span>
        {:else}
          <Play class="w-3.5 h-3.5 fill-current" />
          <span>Run Benchmark Suite</span>
        {/if}
      </button>
    </div>
  </div>

  <!-- Main Scrollable Area -->
  <div class="flex-1 overflow-y-auto p-6 space-y-6">
    <!-- Top KPI Cards (The RAG Triad) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {#each metrics as metric}
        <div class="p-4 bg-white dark:bg-[#0f1422] rounded-xl border border-neutral-200/90 dark:border-neutral-800 shadow-2xs space-y-2">
          <div class="flex items-center justify-between text-xs text-neutral-500 font-mono">
            <span>{metric.name}</span>
            <span class="text-emerald-600 dark:text-emerald-400 font-semibold">{metric.change}</span>
          </div>
          <div class="text-2xl font-bold font-mono text-neutral-900 dark:text-neutral-100">
            {metric.name.includes('Latency') ? `${metric.score}ms` : `${metric.score}%`}
          </div>
          <p class="text-[11px] text-neutral-400 line-clamp-2 leading-relaxed">
            {metric.description}
          </p>
        </div>
      {/each}
    </div>

    <!-- Benchmark Tuner & Test Cases Section -->
    <div class="bg-white dark:bg-[#0f1422] rounded-xl border border-neutral-200/90 dark:border-neutral-800 shadow-2xs p-5 space-y-4">
      <!-- Toolbar & Filters -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-100 dark:border-neutral-800/80 pb-3">
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200/80 dark:border-neutral-700 text-xs">
            <button
              type="button"
              onclick={() => (filterStatus = 'all')}
              class="px-2.5 py-1 rounded-md transition-colors cursor-pointer {filterStatus === 'all'
                ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 shadow-xs font-semibold'
                : 'text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
            >
              All ({testCases.length})
            </button>
            <button
              type="button"
              onclick={() => (filterStatus = 'passed')}
              class="px-2.5 py-1 rounded-md transition-colors cursor-pointer {filterStatus === 'passed'
                ? 'bg-white dark:bg-neutral-900 text-emerald-600 font-semibold shadow-xs'
                : 'text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
            >
              Passed ({passedCount})
            </button>
            <button
              type="button"
              onclick={() => (filterStatus = 'review')}
              class="px-2.5 py-1 rounded-md transition-colors cursor-pointer {filterStatus === 'review'
                ? 'bg-white dark:bg-neutral-900 text-amber-600 font-semibold shadow-xs'
                : 'text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
            >
              Review ({reviewCount})
            </button>
          </div>

          <!-- Reranker Toggle -->
          <label class="flex items-center gap-1.5 px-3 py-1 bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs text-neutral-700 dark:text-neutral-300 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={enableReranker}
              class="rounded text-blue-600 focus:ring-0 cursor-pointer"
            />
            <span class="font-mono text-[11px]">BGE Cross-Reranker</span>
          </label>
        </div>

        <!-- Search Bar -->
        <div class="relative">
          <Search class="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search test queries or expected sources..."
            bind:value={searchQuery}
            class="pl-8 pr-3 py-1.5 text-xs bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 w-64 focus:outline-hidden"
          />
        </div>
      </div>

      <!-- Test Cases Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-neutral-200 dark:border-neutral-800 text-[10px] uppercase font-mono text-neutral-400">
              <th class="py-2.5 px-3">Status</th>
              <th class="py-2.5 px-3">Test Query</th>
              <th class="py-2.5 px-3">Target Scope</th>
              <th class="py-2.5 px-3">Expected Ground Truth</th>
              <th class="py-2.5 px-3 text-center">Context</th>
              <th class="py-2.5 px-3 text-center">Grounded</th>
              <th class="py-2.5 px-3 text-center">Answer</th>
              <th class="py-2.5 px-3 text-right">Latency</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 dark:divide-neutral-800/60 font-mono">
            {#each filteredTestCases as tc (tc.id)}
              <tr
                onclick={() => (selectedTestCase = tc)}
                class="hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors cursor-pointer {selectedTestCase?.id === tc.id ? 'bg-blue-50/40 dark:bg-blue-950/20' : ''}"
              >
                <td class="py-3 px-3">
                  {#if tc.status === 'passed'}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      <Check class="w-3 h-3" />
                      <span>PASS</span>
                    </span>
                  {:else}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                      <AlertTriangle class="w-3 h-3" />
                      <span>REVIEW</span>
                    </span>
                  {/if}
                </td>
                <td class="py-3 px-3 font-sans font-medium text-neutral-900 dark:text-neutral-100 max-w-xs truncate">
                  {tc.query}
                </td>
                <td class="py-3 px-3 text-neutral-500 text-[11px]">
                  {tc.targetCollection}
                </td>
                <td class="py-3 px-3 text-neutral-600 dark:text-neutral-300 text-[11px] truncate max-w-[200px]">
                  {tc.expectedSource}
                </td>
                <td class="py-3 px-3 text-center {tc.contextRelevance >= 90 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}">
                  {tc.contextRelevance}%
                </td>
                <td class="py-3 px-3 text-center {tc.groundedness >= 95 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}">
                  {tc.groundedness}%
                </td>
                <td class="py-3 px-3 text-center {tc.answerRelevance >= 90 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}">
                  {tc.answerRelevance}%
                </td>
                <td class="py-3 px-3 text-right text-neutral-400 text-[11px]">
                  {tc.latencyMs}ms
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
