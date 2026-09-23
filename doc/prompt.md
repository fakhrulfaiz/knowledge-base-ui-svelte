# Cognify Knowledge Base UI — Architecture & Template Guide

> **Note for AI Planning & Implementation Agents**:
> This repository is an **Enterprise Knowledge Base & Retrieval UI Template** built with **Svelte 5** and **Tailwind CSS v4**.
> It is designed as a modular, production-ready frontend template ready to be connected to backend microservices (Internal Drive, Document Extractor, Vector Search & Knowledge Ingestion, and Resource Governance).
> **Do not assume fixed REST endpoints or API paths.** Your backend may use REST, GraphQL, gRPC-Web, or an internal RPC framework. Connect this template by replacing the mock state and handlers in [`src/App.svelte`](file:///e:/Projects/knowledge-base-ui/src/App.svelte) or creating an adapter service layer.

---

## 1. Technology Stack & Key Rules

- **Framework**: **Svelte 5** (Runes mode).
  - Use modern Svelte 5 runes: `$state`, `$derived`, `$derived.by`, `$props`, `$effect`.
  - **Never** use legacy Svelte 3/4 syntax (`export let`, `let:`, reactive statements `$:`) or React syntax.
- **Styling**: **Tailwind CSS v4** (`@tailwindcss/vite`), standard enterprise utilities in `src/index.css`:
  - `.custom-scrollbar`: 5px rounded thumb, transparent track, cross-browser compatibility.
  - `.no-scrollbar`: Utility to hide default scrollbars.
- **Icons**: `@lucide/svelte` / `lucide-svelte`.
- **Tooling**: Vite 6, TypeScript 5, `svelte-check`.
- **UI Design System**: Enterprise-grade, clean, understated, high-contrast, fully responsive (mobile, tablet, desktop).

---

## 2. System Architecture & Domain Concepts

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             UI Application (Template)                       │
│                           src/App.svelte (Controller)                       │
└──────────────┬──────────────────┬───────────────────┬───────────────────────┘
               │                  │                   │
               ▼                  ▼                   ▼
     ┌──────────────────┐  ┌─────────────┐  ┌─────────────────────────┐
     │ Corporate Drive  │  │  Extractor  │  │  Knowledge Base Service │
     │     Service      │  │   Service   │  │ (Chunker & Embeddings)  │
     └────────┬─────────┘  └──────┬──────┘  └───────────┬─────────────┘
              │                   │                     │
              │   1. Browse Files │   2. OCR / Parse    │  3. Ingest Chunks
              └───────────────────┴─────────────────────┘
```

### A. Three-Tier Scope Model
All collections and corporate drive resources belong to one of three organizational scopes:
1. **Personal (`mine`)**: Private to the logged-in user. Has an individual storage cap (e.g. 5 GB).
2. **Team (`team`)**: Scoped to specific functional teams (e.g. *Core AI Infrastructure*, *Security Architecture Council*). Quotas are allocated per team.
3. **Organization (`org`)**: Shared organization-wide across all company members.

### B. Two-Stage Document Pipeline (Corporate Drive &rarr; Knowledge Base)
The UI models a realistic enterprise pipeline where raw files cannot be directly ingested into vector storage without preprocessing:
1. **Drive Exploration**: Users browse scoped corporate drive folders (`Personal Drive`, `Team Drive`, `Organization Drive`).
2. **Extractor Service**: Raw documents (`.pdf`, `.docx`, `.md`) are tracked via `extractorStatus`:
   - `'not_extracted'` (Raw): Needs layout extraction and OCR.
   - `'extracting'`: Processing in progress.
   - `'extracted'` (Ready): Text, pages, and metadata are ready for ingestion.
3. **Knowledge Ingestion**: Only extracted files can be ingested into vector storage. The UI allows users to trigger extraction on-demand (`[Extract]`) or batch (`Extract & Ingest`).

### C. Semantic Retrieval & Search Engine
The search interface ([`src/components/SearchView.svelte`](file:///e:/Projects/knowledge-base-ui/src/components/SearchView.svelte)) supports three retrieval strategies:
- **Hybrid**: Blends dense vector embeddings with lexical keyword matches (e.g. Reciprocal Rank Fusion / RRF).
- **Dense**: Vector cosine similarity over semantic passage representations.
- **Lexical**: Exact keyword matching and BM25 term frequency.
- **Filtering**: Multi-scope filtering (`All`, `Personal`, `Team`, `Organization`), selectable team filter, collection filter, and configurable chunk limits.
- **Citations**: Citations deep-link directly into document pages with highlighted passages.

### D. Governance & Role-Based Access Control (RBAC)
Implemented in [`src/utils/governance.ts`](file:///e:/Projects/knowledge-base-ui/src/utils/governance.ts):
- **`owner` & `admin`**: Full system permissions across all scopes, collections, and quotas. Can access the Admin view.
- **`team_lead`**: Can manage collections and storage quotas for their specific team.
- **`member`**: Standard user; can create personal collections and view assigned team/org collections. Cannot access Admin.
- **`viewer`**: Read-only account. Cannot upload, create, or delete documents. Admin tab is completely hidden.

### E. Storage Resource Quotas
Tracked in gigabytes (GB) via [`src/utils/resourceUtils.ts`](file:///e:/Projects/knowledge-base-ui/src/utils/resourceUtils.ts):
- Organization-wide capacity and utilized storage.
- Team quotas and collection allocations.
- Personal user quotas.
- Upload/ingestion operations pre-check quotas before writing documents.

---

## 3. Directory & Component Map

```
src/
├── main.ts                           # Root mounting with Svelte 5 `mount(App, ...)`
├── App.svelte                        # Root state coordinator, router & modal manager
├── index.css                         # Tailwind CSS v4 & custom scrollbar styles
├── types/
│   └── index.ts                      # Core domain types (Collection, DocumentItem, DriveFile, etc.)
├── data/
│   └── mockData.ts                   # Template mock data (collections, docs, users, drive files)
├── utils/
│   ├── retrieval.ts                  # Hybrid, dense, lexical search simulation
│   ├── chunker.ts                    # Token sliding window chunking & reindex simulation
│   ├── governance.ts                 # RBAC permission check utilities
│   └── resourceUtils.ts              # Quota calculation & byte formatting
└── components/
    ├── Sidebar.svelte                # Responsive navigation rail & slide-out mobile drawer
    ├── HomeView.svelte               # Google Drive style landing page (suggested collections & files)
    ├── CollectionsView.svelte        # Scope-based collection explorer
    ├── CollectionDetailView.svelte   # Document table (with 3-dot ellipsis) & relationship graph
    ├── SearchView.svelte             # Semantic passage search with citation context inspector
    ├── AdminView.svelte              # Storage quotas, token chunking sliders & re-index audit log
    ├── CollectionCard.svelte         # Individual collection card
    ├── DocumentGridCardPreview.svelte# Grid document preview card
    ├── DocumentViewerModal.svelte    # Deep-linking PDF document viewer
    ├── PdfPageThumbnail.svelte       # Simulated PDF raster canvas with highlighted chunks
    ├── DrivePickerModal.svelte       # Corporate Drive 2-stage Extractor & Ingestion modal
    ├── UploadModal.svelte            # Local file upload modal with validation
    ├── NewCollectionModal.svelte     # Collection creation modal
    └── TeamAllocationModal.svelte    # Team quota slider modal
```

---

## 4. How to Connect This Template to Your Backend

When integrating this UI template with your existing backend:

1. **State Injection Point (`src/App.svelte`)**:
   - `App.svelte` currently initializes state using mock arrays from `src/data/mockData.ts` (`collections`, `documents`, `currentUser`, `scopeResourceAllocation`, `teamAllocations`).
   - Replace or populate these with calls to your backend API, SDK, or GraphQL client inside an `$effect` rune or `onMount`.
2. **Drive & Extractor Modal (`src/components/DrivePickerModal.svelte`)**:
   - Swap the local `DRIVE_FOLDERS` and `DRIVE_FILES` with queries to your internal Drive service.
   - When a user clicks `[Extract]`, call your Extractor service to start the extraction task.
   - When ingesting, send the selected file references to your Knowledge Base ingestion pipeline.
3. **Search Page (`src/components/SearchView.svelte`)**:
   - In `handleSearch()`, replace `executeChunkSearch(...)` with a call to your vector/hybrid search engine.
4. **Direct File Upload (`src/components/UploadModal.svelte`)**:
   - Replace the local simulated chunker with your document upload/ingestion endpoint.
5. **Admin & Governance (`src/components/AdminView.svelte`)**:
   - Connect the token chunk size sliders, re-indexing triggers, and team quota distributions to your backend governance service.

---

## 5. UI Layout Conventions to Preserve

- **Mobile & Tablet Drawer**:
  - The sidebar is responsive. On `< md` screens, it is hidden by default and opens as a slide-out drawer via the top mobile bar's hamburger button (`Menu`).
- **Compact Header Theme Toggle**:
  - The dark/light mode toggle is an icon button (`Sun`/`Moon`) in the sidebar header to preserve vertical space in the footer.
- **Three-Dot Ellipsis Truncation**:
  - In `CollectionDetailView.svelte`, document titles and summaries must maintain `truncate` so long names terminate in three dots (`...`) instead of wrapping or overflowing.
  - The table uses `overflow-x-auto custom-scrollbar` to support horizontal scrolling on tablets and phones.

---

## 6. Verification Commands

```bash
# Verify Svelte 5 and TypeScript diagnostics (keep at 0 errors, 0 warnings)
npm run check

# Verify production bundle build
npm run build

# Run local development server
npm run dev
```
