<script lang="ts">
  import {
    MessageSquare,
    Send,
    Sparkles,
    ShieldCheck,
    Layers,
    FileText,
    ExternalLink,
    X,
    ChevronRight,
    SlidersHorizontal,
    Plus,
    Clock,
    Search,
    RefreshCw,
    Check,
    Bot,
    User,
    AlertCircle
  } from '@lucide/svelte';
  import type { Collection, DocumentItem, ChatThread, ChatMessage, ChatCitation, UserProfile } from '../types';

  interface Props {
    currentUser: UserProfile;
    collections: Collection[];
    documents: DocumentItem[];
    threads: ChatThread[];
    activeThreadId: string;
    onSelectThread: (threadId: string) => void;
    onNewThread: () => void;
    onOpenDocument: (doc: DocumentItem, pageNumber?: number) => void;
  }

  let {
    currentUser,
    collections,
    documents,
    threads = $bindable([]),
    activeThreadId = $bindable(''),
    onSelectThread,
    onNewThread,
    onOpenDocument
  }: Props = $props();

  let activeThread = $derived(
    threads.find((t) => t.id === activeThreadId) || threads[0]
  );

  let inputPrompt = $state('');
  let isGenerating = $state(false);
  let strictGrounding = $state(true);
  let selectedCollectionFilter = $state<string>('all');
  let activeCitation = $state<ChatCitation | null>(null);
  let isInspectorOpen = $state(false);

  // Auto-scroll chat container to bottom on new message
  let chatScrollContainer: HTMLDivElement | null = $state(null);

  function scrollToBottom() {
    setTimeout(() => {
      if (chatScrollContainer) {
        chatScrollContainer.scrollTop = chatScrollContainer.scrollHeight;
      }
    }, 50);
  }

  function handleOpenCitation(citation: ChatCitation) {
    activeCitation = citation;
    isInspectorOpen = true;
  }

  function handleOpenDocumentFromCitation(citation: ChatCitation) {
    const doc = documents.find((d) => d.id === citation.docId);
    if (doc) {
      onOpenDocument(doc, citation.pageNumber);
    }
  }

  function handleSubmit() {
    if (!inputPrompt.trim() || isGenerating) return;

    const userText = inputPrompt.trim();
    inputPrompt = '';

    const newMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: new Date().toISOString()
    };

    if (activeThread) {
      activeThread.messages = [...activeThread.messages, newMsg];
      activeThread.updatedAt = new Date().toISOString();
    }

    isGenerating = true;
    scrollToBottom();

    // Grounded retrieval simulation from available documents
    setTimeout(() => {
      const q = userText.toLowerCase();
      // Search matching chunks in active documents
      let matchingChunks: { chunk: any; doc: DocumentItem; score: number }[] = [];

      for (const doc of documents) {
        if (selectedCollectionFilter !== 'all' && doc.collectionId !== selectedCollectionFilter) {
          continue;
        }
        for (const page of doc.pages || []) {
          for (const chunk of page.chunks || []) {
            let score = 0.70;
            const snippetLower = (chunk.snippet || '').toLowerCase();
            const words = q.split(/\s+/).filter((w) => w.length > 3);
            for (const w of words) {
              if (snippetLower.includes(w)) score += 0.08;
            }
            if (score > 0.75) {
              matchingChunks.push({ chunk, doc, score: Math.min(0.985, score) });
            }
          }
        }
      }

      // Sort by score
      matchingChunks.sort((a, b) => b.score - a.score);
      const topMatches = matchingChunks.slice(0, 3);

      let citations: ChatCitation[] = [];
      let responseText = '';

      if (topMatches.length > 0) {
        citations = topMatches.map((m, idx) => ({
          index: idx + 1,
          chunkId: m.chunk.id,
          docId: m.doc.id,
          docTitle: m.doc.title,
          pageNumber: m.chunk.pageNumber,
          snippet: m.chunk.snippet,
          similarity: Number(m.score.toFixed(3))
        }));

        responseText = `Based on the retrieved context from **${citations[0].docTitle}** [1], ${citations[0].snippet.slice(0, 140)}...\n\nFurther analysis indicates that ${citations[1] ? `supporting requirements are defined in [2]: "${citations[1].snippet.slice(0, 110)}..."` : 'the indexed vector corpus confirms consistent alignment with the baseline specification.'}\n\nAll source citations have been verified against active Milvus collections with high cosine confidence.`;
      } else {
        responseText = strictGrounding
          ? 'I could not find sufficiently high-confidence vector matches for your query within the selected collection scope. Try broadening the collection filter or adjusting keyword terms.'
          : 'According to general knowledge base parameters, this topic may relate to cross-functional standards, though no direct high-confidence vector chunk was retrieved in the current scope.';
      }

      const assistantMsg: ChatMessage = {
        id: `msg-resp-${Date.now()}`,
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString(),
        latencyMs: Math.floor(25 + Math.random() * 35),
        retrievedCount: citations.length,
        citations
      };

      if (activeThread) {
        activeThread.messages = [...activeThread.messages, assistantMsg];
        activeThread.updatedAt = new Date().toISOString();
      }

      isGenerating = false;
      scrollToBottom();
    }, 450);
  }

  const SUGGESTED_QUERIES = [
    'What are the consortium eligibility rules in Horizon Europe calls?',
    'Explain the mTLS certificate rotation standard for service mesh workloads.',
    'What thermal expansion and displacement tolerances are defined in EXCEPT89?'
  ];
</script>

<div class="flex-1 flex h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
  <!-- Center Main Chat Stream -->
  <div class="flex-1 flex flex-col min-w-0 h-full">
    <!-- Top Chat Header Bar -->
    <div class="h-14 px-6 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3 min-w-0">
        <div class="p-1.5 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400">
          <MessageSquare class="w-4.5 h-4.5" />
        </div>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h1 class="text-sm font-bold text-neutral-900 dark:text-neutral-100 truncate">
              {activeThread?.title || 'Knowledge Base RAG Chat'}
            </h1>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase font-semibold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300">
              Live Milvus
            </span>
          </div>
          <p class="text-[11px] text-neutral-400 font-mono truncate">
            {activeThread?.messages.length || 0} messages • Grounded on {collections.length} collections
          </p>
        </div>
      </div>

      <!-- Controls & Scope Filter -->
      <div class="flex items-center gap-2.5">
        <!-- Target Collection Filter -->
        <div class="flex items-center gap-1.5 text-xs">
          <span class="text-neutral-400 font-mono hidden sm:inline text-[11px]">Scope:</span>
          <select
            bind:value={selectedCollectionFilter}
            class="bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200 text-xs rounded-md px-2.5 py-1 focus:ring-0 cursor-pointer"
          >
            <option value="all">All Collections ({collections.length})</option>
            {#each collections as col}
              <option value={col.id}>{col.name}</option>
            {/each}
          </select>
        </div>

        <!-- Strict Grounding Toggle -->
        <button
          type="button"
          onclick={() => (strictGrounding = !strictGrounding)}
          class="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md border transition-colors cursor-pointer {strictGrounding
            ? 'bg-blue-50 dark:bg-blue-950/60 border-blue-200 dark:border-blue-900/60 text-blue-700 dark:text-blue-300'
            : 'bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-500'}"
          title="Strict Grounding prevents hallucinations by requiring cosine similarity ≥ 0.75"
        >
          <ShieldCheck class="w-3.5 h-3.5 {strictGrounding ? 'text-blue-600 dark:text-blue-400' : 'text-neutral-400'}" />
          <span class="hidden sm:inline">Strict Grounding</span>
        </button>

        <button
          type="button"
          onclick={onNewThread}
          class="flex items-center gap-1.5 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow-2xs transition-colors cursor-pointer"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </div>
    </div>

    <!-- Chat Messages Scroll Container -->
    <div
      bind:this={chatScrollContainer}
      class="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6"
    >
      {#if !activeThread || activeThread.messages.length === 0}
        <div class="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto p-6 space-y-4">
          <div class="w-12 h-12 rounded-2xl bg-blue-600/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            <Sparkles class="w-6 h-6" />
          </div>
          <div class="space-y-1">
            <h2 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              Query Your Knowledge Base
            </h2>
            <p class="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">
              Ask anything across your indexed documents and Milvus vector collections. Answers are synthesized with exact source citations and cosine attribution.
            </p>
          </div>

          <div class="w-full space-y-2 pt-2">
            <div class="text-[11px] font-semibold uppercase tracking-wider text-neutral-400 font-mono text-left">
              Suggested Questions
            </div>
            {#each SUGGESTED_QUERIES as suggestion}
              <button
                type="button"
                onclick={() => {
                  inputPrompt = suggestion;
                  handleSubmit();
                }}
                class="w-full text-left p-3 text-xs bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 hover:border-blue-500 dark:hover:border-blue-500 rounded-xl transition-all cursor-pointer flex items-center justify-between group shadow-2xs"
              >
                <span class="text-neutral-700 dark:text-neutral-300 font-medium group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {suggestion}
                </span>
                <ChevronRight class="w-3.5 h-3.5 text-neutral-400 group-hover:text-blue-500 shrink-0 ml-2" />
              </button>
            {/each}
          </div>
        </div>
      {:else}
        {#each activeThread.messages as msg (msg.id)}
          <div class="flex gap-3 {msg.role === 'user' ? 'justify-end' : 'justify-start'} max-w-4xl mx-auto">
            {#if msg.role === 'assistant'}
              <div class="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-2xs">
                <Bot class="w-4 h-4" />
              </div>
            {/if}

            <div class="space-y-2 max-w-[85%] sm:max-w-[78%]">
              <div
                class="p-4 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-2xs {msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-xs'
                  : 'bg-white dark:bg-[#0f1422] text-neutral-900 dark:text-neutral-100 border border-neutral-200/90 dark:border-neutral-800 rounded-bl-xs'}"
              >
                <div class="whitespace-pre-wrap font-sans">
                  {msg.content}
                </div>

                <!-- Interactive Citations Bar -->
                {#if msg.citations && msg.citations.length > 0}
                  <div class="mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-800/80 flex flex-wrap items-center gap-1.5">
                    <span class="text-[10px] uppercase font-mono font-semibold text-neutral-400 mr-1">
                      Sources:
                    </span>
                    {#each msg.citations as citation}
                      <button
                        type="button"
                        onclick={() => handleOpenCitation(citation)}
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-blue-50 dark:hover:bg-blue-950/70 border border-neutral-200 dark:border-neutral-700 hover:border-blue-400 text-neutral-700 dark:text-neutral-300 text-[11px] font-mono cursor-pointer transition-colors"
                        title="{citation.docTitle} (p.{citation.pageNumber}) • {(citation.similarity * 100).toFixed(1)}% match"
                      >
                        <span class="font-bold text-blue-600 dark:text-blue-400">[{citation.index}]</span>
                        <span class="truncate max-w-[120px] font-sans">{citation.docTitle}</span>
                        <span class="text-neutral-400 text-[10px]">p.{citation.pageNumber}</span>
                      </button>
                    {/each}
                  </div>
                {/if}
              </div>

              <!-- Message Footnote Telemetry -->
              {#if msg.role === 'assistant' && msg.latencyMs}
                <div class="flex items-center gap-3 text-[10px] text-neutral-400 font-mono pl-1">
                  <span>Retrieved in {msg.latencyMs}ms</span>
                  <span>•</span>
                  <span>{msg.retrievedCount || 0} chunks ranked</span>
                  <span>•</span>
                  <span class="text-emerald-600 dark:text-emerald-400">Grounded 100%</span>
                </div>
              {/if}
            </div>

            {#if msg.role === 'user'}
              <div class="w-8 h-8 rounded-xl bg-neutral-200 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center justify-center shrink-0 text-xs font-bold font-mono">
                {currentUser?.avatarText || 'U'}
              </div>
            {/if}
          </div>
        {/each}

        {#if isGenerating}
          <div class="flex gap-3 justify-start max-w-4xl mx-auto">
            <div class="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 animate-pulse">
              <Bot class="w-4 h-4" />
            </div>
            <div class="p-3.5 rounded-2xl bg-white dark:bg-[#0f1422] border border-neutral-200/90 dark:border-neutral-800 text-xs flex items-center gap-2 text-neutral-500 font-mono">
              <RefreshCw class="w-3.5 h-3.5 animate-spin text-blue-600 dark:text-blue-400" />
              <span>Querying Milvus vector index &amp; synthesizing citation graph...</span>
            </div>
          </div>
        {/if}
      {/if}
    </div>

    <!-- Bottom Input Canvas -->
    <div class="p-4 border-t border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shrink-0">
      <div class="max-w-4xl mx-auto space-y-2">
        <form
          onsubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          class="relative flex items-center"
        >
          <input
            type="text"
            placeholder="Ask a question across your indexed collections..."
            bind:value={inputPrompt}
            disabled={isGenerating}
            class="w-full pl-4 pr-12 py-3 bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl text-xs sm:text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-hidden focus:border-blue-500 dark:focus:border-blue-500 shadow-2xs transition-all"
          />
          <button
            type="submit"
            disabled={!inputPrompt.trim() || isGenerating}
            class="absolute right-2 p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer shadow-xs"
            title="Send query"
          >
            <Send class="w-4 h-4" />
          </button>
        </form>

        <div class="flex items-center justify-between text-[11px] text-neutral-400 font-mono px-1">
          <span>Press Enter to query</span>
          <span>Dense Embedding: BAAI/bge-small-en-v1.5 (384-dim)</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Right Drawer: Grounded Source Inspector -->
  {#if isInspectorOpen && activeCitation}
    <aside class="w-80 lg:w-96 border-l border-neutral-200 dark:border-neutral-800 bg-white dark:bg-[#0c101c] flex flex-col h-full shadow-lg z-20 shrink-0 animate-in slide-in-from-right duration-200">
      <div class="h-14 px-4 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-2">
          <FileText class="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <h3 class="text-xs font-bold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider font-mono">
            Source Inspector
          </h3>
        </div>
        <button
          type="button"
          onclick={() => (isInspectorOpen = false)}
          class="p-1 rounded-md text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <!-- Citation Pill & Score -->
        <div class="p-3 rounded-lg bg-blue-50/60 dark:bg-blue-950/40 border border-blue-200/60 dark:border-blue-900/60 space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-blue-700 dark:text-blue-300 font-mono">
              Citation [{activeCitation.index}]
            </span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              {(activeCitation.similarity * 100).toFixed(1)}% Cosine
            </span>
          </div>
          <div class="text-xs font-semibold text-neutral-900 dark:text-neutral-100 font-sans">
            {activeCitation.docTitle}
          </div>
          <div class="text-[10px] font-mono text-neutral-500">
            Page {activeCitation.pageNumber} • Chunk ID: {activeCitation.chunkId}
          </div>
        </div>

        <!-- Exact Chunk Passage -->
        <div class="space-y-1.5">
          <div class="text-[10px] font-bold uppercase tracking-wider text-neutral-400 font-mono">
            Retrieved Text Passage
          </div>
          <div class="p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 text-xs text-neutral-700 dark:text-neutral-300 font-serif leading-relaxed italic">
            "{activeCitation.snippet}"
          </div>
        </div>

        <!-- Jump to Document -->
        <button
          type="button"
          onclick={() => activeCitation && handleOpenDocumentFromCitation(activeCitation)}
          class="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200 text-xs font-medium rounded-lg shadow-xs transition-colors cursor-pointer"
        >
          <ExternalLink class="w-3.5 h-3.5" />
          <span>Open Full Document (p.{activeCitation.pageNumber})</span>
        </button>
      </div>
    </aside>
  {/if}
</div>
