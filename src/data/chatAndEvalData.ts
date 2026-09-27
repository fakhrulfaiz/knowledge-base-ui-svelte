import type { ChatThread, EvalMetric, EvalTestCase } from '../types';

export const INITIAL_CHAT_THREADS: ChatThread[] = [
  {
    id: 'thread-1',
    title: 'Horizon Europe CORDIS Grants Criteria',
    createdAt: '2026-09-26T14:32:00Z',
    updatedAt: '2026-09-26T16:45:00Z',
    collectionId: 'all',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: 'What are the key funding eligibility rules and consortium requirements for Horizon Europe digital infrastructure calls?',
        timestamp: '2026-09-26T14:32:00Z'
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: 'Based on the indexed European Commission documentation [1], Horizon Europe digital infrastructure calls require a minimum consortium of at least three independent legal entities established in different EU Member States or Associated Countries [2].\n\nKey criteria include:\n1. **TRL Progression**: Proposals must advance technologies from TRL 4 (validation in laboratory) to TRL 6-7 (demonstration in relevant environment) [3].\n2. **Open Science & Data Management**: All peer-reviewed publications must be open access, and research data must adhere to FAIR principles [1].\n3. **Financial Contribution**: Standard funding rate is 100% of eligible costs for Research and Innovation Actions (RIA), and 70% for Innovation Actions (IA) for profit-making entities.',
        timestamp: '2026-09-26T14:32:08Z',
        latencyMs: 48,
        retrievedCount: 4,
        citations: [
          {
            index: 1,
            chunkId: 'chunk-cordis-101',
            docId: 'doc-cordis-core',
            docTitle: 'CORDIS Horizon Europe Work Programme 2024-2025',
            pageNumber: 14,
            snippet: 'Eligibility conditions require consortia to include at least one independent legal entity established in a Member State, and at least two other independent legal entities each established in different Member States or Associated Countries.',
            similarity: 0.954
          },
          {
            index: 2,
            chunkId: 'chunk-cordis-108',
            docId: 'doc-cordis-core',
            docTitle: 'CORDIS Horizon Europe Work Programme 2024-2025',
            pageNumber: 19,
            snippet: 'Innovation Actions shall deliver solutions validated in operational operational environments, targeting TRL 7 by project completion.',
            similarity: 0.931
          },
          {
            index: 3,
            chunkId: 'chunk-cordis-112',
            docId: 'doc-cordis-financial',
            docTitle: 'EU Model Grant Agreement Financial Guidelines',
            pageNumber: 32,
            snippet: 'Direct personnel costs, subcontracting, and purchase costs are reimbursed at 100% for non-profit entities and RIAs, with 25% flat-rate indirect cost calculation.',
            similarity: 0.918
          }
        ]
      }
    ]
  },
  {
    id: 'thread-2',
    title: 'Zero Trust mTLS Certificate Rotation',
    createdAt: '2026-09-25T10:15:00Z',
    updatedAt: '2026-09-25T11:02:00Z',
    collectionId: 'col-org-1',
    messages: [
      {
        id: 'msg-3',
        role: 'user',
        content: 'What is the required rotation interval for service mesh mTLS certificates and which cipher suites are permitted?',
        timestamp: '2026-09-25T10:15:00Z'
      },
      {
        id: 'msg-4',
        role: 'assistant',
        content: 'According to the Enterprise Zero Trust & Identity Standards [1], all service-to-service communication within the mesh must enforce ephemeral identity credentials:\n\n- **Rotation Interval**: Microservice certificates issued by SPIFFE/SPIRE must rotate every **24 hours** (with graceful overlap windows starting at 18 hours) [1].\n- **Cryptographic Algorithms**: Only TLS 1.3 is permitted. The allowed cipher suites are restricted to:\n  - `TLS_AES_256_GCM_SHA384`\n  - `TLS_CHACHA20_POLY1305_SHA256` [2].\n- **Revocation**: CRLs are prohibited; automated short-lived TTLs are mandated to eliminate revocation latency overhead.',
        timestamp: '2026-09-25T10:15:05Z',
        latencyMs: 34,
        retrievedCount: 3,
        citations: [
          {
            index: 1,
            chunkId: 'chunk-zt-201',
            docId: 'doc-zt-identity',
            docTitle: 'Zero Trust Architecture: Service Mesh Security v3.2',
            pageNumber: 8,
            snippet: 'All X.509 SVIDs issued to workloads must have a maximum lifetime of 24 hours. The SPIRE workload agent initiates renewal when 75% of the certificate validity period has elapsed.',
            similarity: 0.971
          },
          {
            index: 2,
            chunkId: 'chunk-zt-205',
            docId: 'doc-zt-crypto',
            docTitle: 'Cryptographic Protocols & Transport Encryption Standard',
            pageNumber: 3,
            snippet: 'TLS 1.2 is deprecated for all inter-service mesh traffic. Implementations MUST negotiate TLS 1.3 with AEAD cipher suites (AES-GCM or ChaCha20-Poly1305).',
            similarity: 0.963
          }
        ]
      }
    ]
  },
  {
    id: 'thread-3',
    title: 'EXCEPT89 Mechanical Tolerance Analysis',
    createdAt: '2026-09-24T18:05:00Z',
    updatedAt: '2026-09-24T18:22:00Z',
    collectionId: 'col-except89',
    messages: [
      {
        id: 'msg-5',
        role: 'user',
        content: 'What are the thermal boundary conditions and expansion tolerances specified in EXCEPT89?',
        timestamp: '2026-09-24T18:05:00Z'
      },
      {
        id: 'msg-6',
        role: 'assistant',
        content: 'In the EXCEPT89 engineering specification [1], thermal variance modeling is established across -40°C to +85°C operational envelopes:\n\n- **Joint Expansion Tolerance**: ±14.5 mm axial displacement under dynamic peak wind shear [1].\n- **Material Fatigue Threshold**: 2.4 × 10⁶ cyclic oscillations prior to inspection trigger [2].',
        timestamp: '2026-09-24T18:05:06Z',
        latencyMs: 41,
        retrievedCount: 2,
        citations: [
          {
            index: 1,
            chunkId: 'chunk-ex-04',
            docId: 'doc-except89',
            docTitle: 'EXCEPT89 Engineering Analysis & Thermal Envelope',
            pageNumber: 4,
            snippet: 'Thermal expansion coefficients dictate minimum expansion gap spacing of 14.5 mm at nominal reference temperature (20°C).',
            similarity: 0.948
          },
          {
            index: 2,
            chunkId: 'chunk-ex-07',
            docId: 'doc-except89',
            docTitle: 'EXCEPT89 Engineering Analysis & Thermal Envelope',
            pageNumber: 7,
            snippet: 'Fatigue testing under ASTM E606 confirms structural endurance beyond 2,400,000 stress cycles before localized crack propagation.',
            similarity: 0.925
          }
        ]
      }
    ]
  }
];

export const INITIAL_EVAL_METRICS: EvalMetric[] = [
  {
    name: 'Context Relevance',
    score: 94.2,
    change: '+2.4%',
    status: 'optimal',
    description: 'Proportion of retrieved chunks directly contributing to the answer without noise.'
  },
  {
    name: 'Groundedness / Faithfulness',
    score: 98.6,
    change: '+0.8%',
    status: 'optimal',
    description: 'Verification that all statements are strictly supported by retrieved vector chunks.'
  },
  {
    name: 'Answer Relevance',
    score: 95.1,
    change: '+1.5%',
    status: 'optimal',
    description: 'Degree to which the generated synthesis directly addresses user intent.'
  },
  {
    name: 'Milvus P95 Latency',
    score: 38,
    change: '-6ms',
    status: 'optimal',
    description: 'HNSW vector search query response time across 1,247 chunks.'
  }
];

export const INITIAL_EVAL_TEST_CASES: EvalTestCase[] = [
  {
    id: 'tc-1',
    query: 'What is the maximum token budget and sliding window overlap?',
    targetCollection: 'Platform Standards',
    expectedSource: 'Enterprise Ingestion & Embedding Protocol',
    actualRetrieved: 'doc-ingest-proto p.2 #chunk-4',
    contextRelevance: 98,
    groundedness: 100,
    answerRelevance: 97,
    latencyMs: 24,
    status: 'passed'
  },
  {
    id: 'tc-2',
    query: 'What are the consortium rules for CORDIS grant participants?',
    targetCollection: 'CORDIS Grants',
    expectedSource: 'CORDIS Horizon Europe Work Programme',
    actualRetrieved: 'doc-cordis-core p.14 #chunk-101',
    contextRelevance: 96,
    groundedness: 99,
    answerRelevance: 95,
    latencyMs: 31,
    status: 'passed'
  },
  {
    id: 'tc-3',
    query: 'What cryptographic cipher suites are enforced in TLS 1.3?',
    targetCollection: 'Zero Trust Architecture',
    expectedSource: 'Cryptographic Protocols Standard',
    actualRetrieved: 'doc-zt-crypto p.3 #chunk-205',
    contextRelevance: 95,
    groundedness: 98,
    answerRelevance: 96,
    latencyMs: 28,
    status: 'passed'
  },
  {
    id: 'tc-4',
    query: 'Explain the displacement tolerance in EXCEPT89 section 4',
    targetCollection: 'EXCEPT89 Dataset',
    expectedSource: 'EXCEPT89 Engineering Analysis',
    actualRetrieved: 'doc-except89 p.4 #chunk-04',
    contextRelevance: 94,
    groundedness: 97,
    answerRelevance: 93,
    latencyMs: 35,
    status: 'passed'
  },
  {
    id: 'tc-5',
    query: 'How are deleted documents garbage-collected in pgvector / Milvus?',
    targetCollection: 'Storage Engine',
    expectedSource: 'Milvus Standalone Operations Manual',
    actualRetrieved: 'doc-milvus-ops p.11 #chunk-88',
    contextRelevance: 89,
    groundedness: 94,
    answerRelevance: 91,
    latencyMs: 42,
    status: 'passed'
  },
  {
    id: 'tc-6',
    query: 'What is the SLA for disaster recovery failover in multi-region clusters?',
    targetCollection: 'SRE Infrastructure',
    expectedSource: 'Disaster Recovery & Business Continuity',
    actualRetrieved: 'doc-sre-dr p.6 #chunk-12',
    contextRelevance: 78,
    groundedness: 86,
    answerRelevance: 82,
    latencyMs: 56,
    status: 'review'
  }
];
