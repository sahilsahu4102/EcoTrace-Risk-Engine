"use client";

import React, { useEffect, useMemo, useState } from "react";
import { ReactFlow, Background, Edge, Node, MarkerType, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { CommodityRegionBreakdown } from "@/lib/api";
import { Mark } from "@/components/form";

interface SupplyChainGraphProps {
  company: string;
  breakdown: CommodityRegionBreakdown[];
}

const INK = "#14181f";
const PAPER = "#f2f2ee";
const PAPER_2 = "#e8e8e1";
const TRADE = "Trase trade records";

const nodeBase = {
  fontFamily: "var(--font-barlow), system-ui, sans-serif",
  fontSize: 14,
  color: INK,
  borderRadius: 0,
  padding: "8px 10px",
  width: 150,
  textAlign: "center" as const,
  boxShadow: "none",
};
// Lines run left to right: countries, then commodities, then the company.
const flow = { sourcePosition: Position.Right, targetPosition: Position.Left };

/** Countries on the left, commodities in the middle, the company on the right.
 *  A solid line is a Trase trade record; a dashed line is a producer-country link. */
export default function SupplyChainGraph({ company, breakdown }: SupplyChainGraphProps) {
  // On a phone the three-column graph cannot fit at a readable size, so the same links
  // are listed grouped by commodity instead.
  // This component only renders in the browser (dynamic import, ssr: false), so window exists.
  const [narrow, setNarrow] = useState(() => window.matchMedia("(max-width: 720px)").matches);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 720px)");
    const sync = () => setNarrow(mq.matches);
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  const { nodes, edges } = useMemo(() => {
    const uniqueRegions = Array.from(new Set(breakdown.map((b) => b.region)));
    const uniqueCommodities = Array.from(new Set(breakdown.map((b) => b.commodity)));

    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    const xSpacing = 270;
    const ySpacing = 72;
    const maxItems = Math.max(uniqueRegions.length, uniqueCommodities.length, 1);
    const midY = (maxItems * ySpacing) / 2;

    const rStartY = midY - (uniqueRegions.length * ySpacing) / 2;
    uniqueRegions.forEach((region, i) => {
      newNodes.push({
        id: `r-${region}`,
        position: { x: 0, y: rStartY + i * ySpacing },
        data: { label: region },
        type: "input",
        ...flow,
        style: { ...nodeBase, background: PAPER_2, border: `1px solid ${INK}` },
      });
    });

    const cStartY = midY - (uniqueCommodities.length * ySpacing) / 2;
    uniqueCommodities.forEach((commodity, i) => {
      newNodes.push({
        id: `c-${commodity}`,
        position: { x: xSpacing, y: cStartY + i * ySpacing },
        data: { label: commodity },
        ...flow,
        style: { ...nodeBase, background: PAPER, border: `2px solid ${INK}`, fontWeight: 600 },
      });

      newEdges.push({
        id: `e-c-${commodity}-comp`,
        source: `c-${commodity}`,
        target: "company",
        style: { stroke: INK, strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: INK },
      });
    });

    newNodes.push({
      id: "company",
      position: { x: xSpacing * 2, y: midY - 20 },
      data: { label: company },
      type: "output",
      ...flow,
      style: { ...nodeBase, width: 170, background: INK, color: PAPER, border: `1px solid ${INK}`, fontWeight: 700, fontSize: 16 },
    });

    breakdown.forEach((b) => {
      const trade = b.evidence === TRADE;
      newEdges.push({
        id: `e-r-${b.region}-c-${b.commodity}`,
        source: `r-${b.region}`,
        target: `c-${b.commodity}`,
        style: { stroke: INK, strokeWidth: 1.25, strokeDasharray: trade ? undefined : "5 4" },
        markerEnd: { type: MarkerType.ArrowClosed, color: INK },
      });
    });

    return { nodes: newNodes, edges: newEdges };
  }, [company, breakdown]);

  if (breakdown.length === 0) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#5a616d" }}>
        No clear supply chain trace available for this company.
      </div>
    );
  }

  if (narrow) {
    const commodities = Array.from(new Set(breakdown.map((b) => b.commodity)));
    return (
      <ul className="chain">
        {commodities.map((c) => (
          <li key={c}>
            <p className="chain-head">
              <b>{c}</b> <span>to {company}</span>
            </p>
            <ul className="chips">
              {breakdown
                .filter((b) => b.commodity === c)
                .map((b) => (
                  <li key={b.region} className="chip">
                    <Mark kind={b.evidence === TRADE ? "solid" : "hollow"} />
                    {b.region}
                  </li>
                ))}
            </ul>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.08 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
      >
        <Background gap={20} size={1} color="#bdb8a8" />
      </ReactFlow>
    </div>
  );
}
