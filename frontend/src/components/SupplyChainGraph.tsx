"use client";

import React, { useMemo } from 'react';
import { ReactFlow, Background, Controls, Edge, Node, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CommodityRegionBreakdown } from '@/lib/api';

interface SupplyChainGraphProps {
  company: string;
  breakdown: CommodityRegionBreakdown[];
}

export default function SupplyChainGraph({ company, breakdown }: SupplyChainGraphProps) {
  // Compute unique regions and commodities from breakdown
  const { nodes, edges } = useMemo(() => {
    // 1. Gather unique
    const uniqueRegions = Array.from(new Set(breakdown.map((b) => b.region)));
    const uniqueCommodities = Array.from(new Set(breakdown.map((b) => b.commodity)));

    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    // Helper functions for positioning
    const xSpacing = 300;
    const ySpacing = 80;

    // Center heights based on counts
    const maxItems = Math.max(uniqueRegions.length, uniqueCommodities.length, 1);
    const canvasHeight = maxItems * ySpacing;
    const midY = canvasHeight / 2;

    // --- Create Source Nodes (Regions) ---
    const rStartY = midY - (uniqueRegions.length * ySpacing) / 2;
    uniqueRegions.forEach((region, i) => {
      newNodes.push({
        id: `r-${region}`,
        position: { x: 50, y: rStartY + i * ySpacing + 20 },
        data: { label: region },
        type: 'input',
        style: {
          background: "var(--card-bg)",
          color: "var(--text-primary)",
          border: "1px solid var(--border-color)",
          borderRadius: "8px",
          padding: "10px",
          width: 140,
          textAlign: "center",
          boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        },
      });
    });

    // --- Create Mid Nodes (Commodities) ---
    const cStartY = midY - (uniqueCommodities.length * ySpacing) / 2;
    uniqueCommodities.forEach((commodity, i) => {
      newNodes.push({
        id: `c-${commodity}`,
        position: { x: 50 + xSpacing, y: cStartY + i * ySpacing + 20 },
        data: { label: commodity },
        style: {
          background: "rgba(16, 185, 129, 0.1)", // emerald tint
          color: "var(--accent-emerald)",
          border: "1px solid rgba(16, 185, 129, 0.3)",
          borderRadius: "20px", // pill shape
          padding: "10px",
          width: 140,
          textAlign: "center",
          fontWeight: "bold",
        },
      });

      // Edge from commodity to company
      newEdges.push({
        id: `e-c-${commodity}-comp`,
        source: `c-${commodity}`,
        target: 'company',
        animated: true,
        style: { stroke: "var(--accent-emerald)", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "var(--accent-emerald)" },
      });
    });

    // --- Create Target Node (Company) ---
    newNodes.push({
      id: 'company',
      position: { x: 50 + xSpacing * 2, y: midY },
      data: { label: company },
      type: 'output',
      style: {
        background: "var(--accent-emerald)",
        color: "#fff",
        border: "none",
        borderRadius: "8px",
        padding: "12px",
        width: 160,
        textAlign: "center",
        fontWeight: "bold",
        fontSize: "1rem",
        boxShadow: "0 0 20px rgba(16, 185, 129, 0.4)",
      },
    });

    // --- Create Edges (Region -> Commodity) ---
    breakdown.forEach((b) => {
      newEdges.push({
        id: `e-r-${b.region}-c-${b.commodity}`,
        source: `r-${b.region}`,
        target: `c-${b.commodity}`,
        animated: true, // indicates flow
        style: { stroke: "var(--text-muted)", strokeWidth: 1.5, strokeDasharray: "5,5" },
        markerEnd: { type: MarkerType.ArrowClosed, color: "var(--text-muted)" },
      });
    });

    return { nodes: newNodes, edges: newEdges };
  }, [company, breakdown]);

  if (breakdown.length === 0) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
        No clear supply chain trace available for this company.
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background gap={16} size={1} color="rgba(255,255,255,0.05)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
