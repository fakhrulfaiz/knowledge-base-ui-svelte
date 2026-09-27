# Milvus Vector Graph Clustering & Layout Architecture Report

> **Project**: Knowledge Base UI / Vector Graph Explorer  
> **Backend**: FastAPI (`server/main.py`), Milvus Standalone (v2.4), FastEmbed (`bge-small-en-v1.5`)  
> **Frontend**: Svelte 5 (Runes), Tailwind CSS v4, HTML5 SVG Canvas  
> **Date**: September 2026  

---

## 1. Executive Summary & Root Cause Analysis

### The Problem
In earlier iterations of the Vector Graph, every document collection displayed the **exact same geometric diamond / flower shape** on the canvas, regardless of what text or topic was inside the document.

```
       [Earlier Geometric Bug]                     [Current Real Vector Layout]
        Identical Diamond Formula                    True 384-Dim PCA Projection
 
             • (Page 1)                                   • (Page 3)
           /   \                                        •    • (Page 1)
 (Page 4) •  ◎  • (Page 2)        ───►              •     ◎ (Doc Hub)
           \   /                                       •      • (Page 8)
             • (Page 3)                                    • (Page 2)
    (Same formula for all files)               (Unique organic cloud per file)
```

### The Root Cause
1. **Centroid-Only Calculation**: Vector distance calculations were originally performed only between **collection centroids** (1 vector per file).
2. **Artificial Chunk Placement**: Chunks belonging to each document were positioned using an artificial polar mathematical formula:
   $$\theta = \frac{\text{chunkIndex}}{\text{totalChunks}} \times 2\pi, \quad r = 38 + ((\text{chunkIndex} \times 17) \bmod 38)$$
3. **No Chunk Vectors in API**: The backend `/api/graph` endpoint queried only metadata fields (`id`, `page_number`, `text`, `doc_name`), without extracting the underlying `vector` field. Consequently, every chunk was given the collection's center coordinate, and the frontend artificially fanned them out in identical geometric patterns.

---

## 2. End-to-End Implementation Architecture

To solve this, the pipeline was re-engineered so that **every single chunk's position is derived from its real 384-dimensional embedding vector**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       1. Milvus Vector Storage (HNSW)                       │
│  - 6 Real Collections | 1,247 Total Vector Chunks | 384-dim BGE Embeddings  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     2. FastAPI Backend (server/main.py)                     │
│  - Retrieve all 384-dim vectors: output_fields=["..., "vector"]             │
│  - Global PCA / SVD Reduction across ALL chunks simultaneously              │
│  - Derive Document Hub Centroid from chunk mass center                      │
│  - Pairwise Centroid Cosine Matrix & Multidimensional Scaling (MDS)         │
│  - Detect Semantic Bridge Links (Similarity >= 82%)                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 3. VectorGraphView.svelte (Interactive SVG)                 │
│  - Direct mapping of (semantic_x, semantic_y) onto canvas coordinate space  │
│  - Organic collision relaxation pass (min distance 18px)                    │
│  - Hover-only edge inspection: floating similarity badge                    │
│  - Enterprise dual-theme support (Dark & Light modes)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Milvus Ingestion & Live Datasets

All mock data was removed. All vectors are stored in Milvus standalone (`http://localhost:19530`) with an `HNSW` index and `COSINE` metric type:

| Collection Name | Document Source | Chunks | Domain Topic | Color |
|---|---|---|---|---|
| `networking_100g_overview` | `100G Networking Slides` | 32 | Optical Transceivers, QSFP28, CFP4 | Sky Blue (`#38bdf8`) |
| `cppcon_unwinding_the_stack` | `CppCon 2018 Slides (James McNellis)` | 198 | Windows C++ Exception Internals, SEH | Purple (`#a855f7`) |
| `cpp_exception_handling_1989` | `except89.pdf (Koenig & Stroustrup)` | 204 | Original C++ Exception Handling Paper (1989) | Rose/Pink (`#ec4899`) |
| `database_queries_data_mining_olap` | `hamel-197-manuscript-final.pdf` | 47 | Relational Queries, OLAP, Multidimensional Cubes | Emerald (`#10b981`) |
| `olap_decision_support_systems` | `Online_Analytical_Processing...pdf` | 106 | Enterprise Decision Support Systems, ROLAP/MOLAP | Cyan (`#06b6d4`) |
| `cordis_eu_research` | `cordis.pdf` | 660 | European Commission Innovation Results | Amber (`#f59e0b`) |

---

## 4. Backend Dimensionality Reduction Engine

Implemented in [server/main.py](file:///e:/Projects/knowledge-base-ui/server/main.py):

### A. Global Chunk PCA (Principal Component Analysis via SVD)
When `/api/graph` loads, it extracts the real 384-dimensional embeddings for all candidate chunks across all target collections and computes a global Singular Value Decomposition:

```python
# 1. Collect all chunk vectors across all collections
vecs = np.array(all_chunk_vectors, dtype=np.float32)  # Shape: (N, 384)

# 2. Zero-center the embedding matrix
vecs_centered = vecs - np.mean(vecs, axis=0)

# 3. Compute Singular Value Decomposition (SVD)
U, S, Vt = np.linalg.svd(vecs_centered, full_matrices=False)

# 4. Extract first 2 principal components
coords_2d = U[:, :2] * S[:2]

# 5. Normalize into [-1, 1] range for canvas projection
max_val = np.max(np.abs(coords_2d))
if max_val > 1e-6:
    coords_2d /= max_val

# 6. Assign unique semantic coordinates to every individual chunk
for i, c_node in enumerate(all_chunk_nodes):
    c_node["semantic_x"] = round(float(coords_2d[i, 0]), 4)
    c_node["semantic_y"] = round(float(coords_2d[i, 1]), 4)
```

### B. True Document Hub Centroid Placement
The Document Hub node and Collection Hub node are positioned at the true center of mass of their constituent chunks:

$$\bar{x}_{\text{doc}} = \frac{1}{|C_{\text{doc}}|} \sum_{c \in C_{\text{doc}}} x_c, \quad \bar{y}_{\text{doc}} = \frac{1}{|C_{\text{doc}}|} \sum_{c \in C_{\text{doc}}} y_c$$

### C. Classical Multidimensional Scaling (MDS) & Semantic Bridges
Centroid-to-centroid cosine distances are measured:
$$D_{ij} = \sqrt{\max(0, 2(1 - \cos(\mathbf{v}_i, \mathbf{v}_j)))}$$

Pairs with high semantic affinity ($\ge 82\%$) automatically receive a cross-document semantic bridge edge:
- **OLAP Twin Cluster**: `database_queries_data_mining_olap` $\leftrightarrow$ `olap_decision_support_systems` (**96.4% cosine similarity**)
- **C++ Exceptions Twin Cluster**: `cpp_exception_handling_1989` $\leftrightarrow$ `cppcon_unwinding_the_stack` (**90.8% cosine similarity**)
- **EU Innovation & OLAP**: `cordis_eu_research` $\leftrightarrow$ `olap_decision_support_systems` (**85.2% cosine similarity**)
- **EU Innovation & Database Queries**: `cordis_eu_research` $\leftrightarrow$ `database_queries_data_mining_olap` (**83.0% cosine similarity**)

---

## 5. Frontend Canvas Rendering & Physics

Implemented in [src/components/VectorGraphView.svelte](file:///e:/Projects/knowledge-base-ui/src/components/VectorGraphView.svelte):

### A. Elimination of Artificial Shapes
The artificial polar loop was deleted. Chunks now map directly to canvas world coordinates:

```typescript
const scaleX = canvasWidth * 0.42;
const scaleY = canvasHeight * 0.42;

rawNodes.forEach((node) => {
  const semX = node.semantic_x ?? 0;
  const semY = node.semantic_y ?? 0;

  const targetX = cx + semX * scaleX;
  const targetY = cy + semY * scaleY;

  node.targetX = targetX;
  node.targetY = targetY;
});
```

### B. Organic Collision Relaxation
To prevent vectors with near-identical embeddings from stacking directly on top of each other, a gentle relaxation pass runs:

```typescript
const minDistance = 18;
for (let iter = 0; iter < 12; iter++) {
  for (let i = 0; i < rawNodes.length; i++) {
    for (let j = i + 1; j < rawNodes.length; j++) {
      const n1 = rawNodes[i];
      const n2 = rawNodes[j];
      const dx = n2.targetX - n1.targetX;
      const dy = n2.targetY - n1.targetY;
      const dist = Math.hypot(dx, dy);
      if (dist < minDistance && dist > 0.0001) {
        const overlap = (minDistance - dist) / 2;
        const angle = Math.atan2(dy, dx);
        n1.targetX -= Math.cos(angle) * overlap;
        n1.targetY -= Math.sin(angle) * overlap;
        n2.targetX += Math.cos(angle) * overlap;
        n2.targetY += Math.sin(angle) * overlap;
      }
    }
  }
}
```

### C. Hover-Only Similarity Inspection (Zero Visual Clutter)
Permanent text bars and static badges on the canvas were removed.
- **Edge Hit Area**: An invisible 14px stroke `<line stroke="transparent" stroke-width="14" />` captures hover events effortlessly.
- **Floating Tooltip**: Hovering an edge renders a floating card showing the connection type and exact cosine similarity (e.g. `96.4% Cosine Similarity`).
- **Node Tooltip**: Hovering any node displays its page number, document name, and search score.

---

## 6. Verification & Results

1. **Topological Truth**:
   - `database_queries` and `olap_decision_support` sit adjacent to each other on the right side of the canvas with a dashed purple bridge.
   - `cppcon_unwinding_the_stack` and `cpp_exception_handling_1989` sit in the lower-left quadrant connected by a bridge.
   - `networking_100g_overview` sits in its own distant optical domain at the top.
   - `cordis_eu_research` occupies the central-left sector.
2. **Individual Shape Diversity**:
   - Each document's cluster exhibits a unique, organic shape reflecting the internal semantic diversity of its paragraphs and pages.
3. **Diagnostics**:
   - `svelte-check`: 0 errors, 0 warnings.
   - Backend Uvicorn service: sub-40ms response latency on global PCA across 60+ nodes.
