"use client";

import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

import { MOCK_GENOME_NODES } from "@/lib/mock-data";

type NodeData = {
  label: string;
  layer: "traditional" | "evidence" | "regulation" | "ip";
  status: string;
  confidence: string;
  description: string;
};

function KnowledgeNode({ data }: { data: NodeData }) {
  const layerClass = {
    traditional: "bg-warm-subtle text-warm",
    evidence: "bg-accent-subtle text-accent",
    regulation: "bg-[#EDF0F4] text-ink",
    ip: "bg-[#EEEAF8] text-[#6652A5]",
  }[data.layer];

  return (
    <div className="w-[250px] rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-surface !bg-accent"
      />

      <div className="flex items-start justify-between gap-2">
        <span
          className={`rounded-full px-2 py-1 text-[10px] font-medium capitalize ${layerClass}`}
        >
          {data.layer}
        </span>

        <span className="font-mono text-[10px] text-ink-muted">
          {data.confidence}
        </span>
      </div>

      <h3 className="mt-3 text-sm font-semibold leading-5 text-ink">
        {data.label}
      </h3>

      <p className="mt-2 line-clamp-4 text-xs leading-5 text-ink-muted">
        {data.description}
      </p>

      <div className="mt-3 border-t border-border pt-3">
        <span className="text-[10px] font-medium capitalize text-ink-muted">
          {data.status.replace("-", " ")}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-surface !bg-accent"
      />
    </div>
  );
}

const nodeTypes = {
  knowledge: KnowledgeNode,
};

export default function TraditionalKnowledgePage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const nodes: Node<NodeData>[] = useMemo(() => {
    const positions = [
      { x: 40, y: 80 },
      { x: 40, y: 300 },
      { x: 40, y: 520 },
      { x: 360, y: 170 },
      { x: 360, y: 390 },
      { x: 690, y: 280 },
      { x: 690, y: 500 },
      { x: 1020, y: 120 },
      { x: 1020, y: 380 },
      { x: 1320, y: 260 },
    ];

    return MOCK_GENOME_NODES.map((item, index) => ({
      id: item.id,
      type: "knowledge",
      position: positions[index] ?? { x: 0, y: 0 },
      data: {
        label: item.label,
        layer: item.layer,
        status: item.status,
        confidence: item.confidence,
        description: item.description,
      },
    }));
  }, []);

  const edges: Edge[] = useMemo(() => {
    return MOCK_GENOME_NODES.flatMap((node) =>
      node.relationships
        .filter((target) =>
          MOCK_GENOME_NODES.some((item) => item.id === target)
        )
        .map((target) => ({
          id: `${node.id}-${target}`,
          source: node.id,
          target,
          type: "smoothstep",
          animated: false,
          style: {
            stroke: "#0F6B5C",
            strokeWidth: 1.5,
          },
        }))
    );
  }, []);

  const selectedNode = MOCK_GENOME_NODES.find(
    (node) => node.id === selectedId
  );

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-[1500px] px-6 py-8 md:px-10 md:py-12">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Traditional Knowledge
          </p>

          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
                What already exists?
              </h1>

              <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
                Explore the relationships between traditional knowledge,
                scientific evidence, regulation, prior art and your
                innovation.
              </p>
            </div>

            <div className="font-mono text-xs text-ink-muted">
              {MOCK_GENOME_NODES.length} connected findings
            </div>
          </div>
        </header>

        {/* LEGEND */}
        <div className="mt-6 flex flex-wrap gap-2">
          <Legend label="Traditional knowledge" tone="traditional" />
          <Legend label="Scientific evidence" tone="evidence" />
          <Legend label="Regulation" tone="regulation" />
          <Legend label="IP / invention" tone="ip" />
        </div>

        {/* GRAPH + DETAILS */}
        <section className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
          <div className="h-[720px] overflow-hidden rounded-3xl border border-border bg-surface">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{
                padding: 0.18,
              }}
              onNodeClick={(_, node) => setSelectedId(node.id)}
              proOptions={{
                hideAttribution: true,
              }}
            >
              <Background
                gap={24}
                size={1}
                color="#E1E5E1"
              />

              <MiniMap
                pannable
                zoomable
                nodeColor="#0F6B5C"
              />

              <Controls />
            </ReactFlow>
          </div>

          {/* DETAILS */}
          <aside className="rounded-3xl border border-border bg-surface p-6">
            {selectedNode ? (
              <>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                    Finding
                  </span>

                  <button
                    type="button"
                    onClick={() => setSelectedId(null)}
                    className="text-xs text-ink-muted hover:text-ink"
                  >
                    Close
                  </button>
                </div>

                <h2 className="mt-4 text-2xl font-semibold leading-tight tracking-tight">
                  {selectedNode.label}
                </h2>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Legend
                    label={selectedNode.layer}
                    tone={selectedNode.layer}
                  />

                  <span className="rounded-full bg-ink/5 px-2.5 py-1 text-[10px] font-medium capitalize text-ink-muted">
                    {selectedNode.status.replace("-", " ")}
                  </span>

                  <span className="rounded-full bg-accent-subtle px-2.5 py-1 text-[10px] font-medium text-accent">
                    {selectedNode.confidence} confidence
                  </span>
                </div>

                <p className="mt-6 text-sm leading-7 text-ink-muted">
                  {selectedNode.description}
                </p>

                <div className="mt-7 border-t border-border pt-6">
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                    Sources
                  </p>

                  <div className="mt-3 space-y-2">
                    {selectedNode.sources.map((source) => (
                      <div
                        key={source}
                        className="rounded-xl border border-border px-3 py-3 text-xs leading-5 text-ink-muted"
                      >
                        {source}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-7 border-t border-border pt-6">
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                    Connected to
                  </p>

                  <div className="mt-3 space-y-2">
                    {selectedNode.relationships.map((relationship) => {
                      const connected = MOCK_GENOME_NODES.find(
                        (node) => node.id === relationship
                      );

                      if (!connected) return null;

                      return (
                        <button
                          key={relationship}
                          type="button"
                          onClick={() => setSelectedId(relationship)}
                          className="block w-full rounded-xl border border-border px-3 py-3 text-left text-xs transition hover:bg-background"
                        >
                          <span className="font-medium text-ink">
                            {connected.label}
                          </span>

                          <span className="mt-1 block text-ink-muted">
                            {connected.layer}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                  Explore the map
                </p>

                <h2 className="mt-3 text-2xl font-semibold tracking-tight">
                  Follow the connections.
                </h2>

                <p className="mt-3 text-sm leading-7 text-ink-muted">
                  Select a node to see what it represents, where its evidence
                  comes from, and how it connects to the rest of the case.
                </p>

                <div className="mt-7 rounded-2xl bg-background p-5">
                  <p className="text-sm font-medium">
                    Start with the centre.
                  </p>

                  <p className="mt-2 text-xs leading-5 text-ink-muted">
                    Then follow the evidence outward. Known traditional use,
                    modern evidence, regulation and potential invention should
                    remain distinct.
                  </p>
                </div>
              </>
            )}
          </aside>
        </section>
      </div>
    </main>
  );
}

function Legend({
  label,
  tone,
}: {
  label: string;
  tone: "traditional" | "evidence" | "regulation" | "ip";
}) {
  const styles = {
    traditional: "bg-warm-subtle text-warm",
    evidence: "bg-accent-subtle text-accent",
    regulation: "bg-[#EDF0F4] text-ink",
    ip: "bg-[#EEEAF8] text-[#6652A5]",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[10px] font-medium capitalize ${styles[tone]}`}
    >
      {label}
    </span>
  );
}