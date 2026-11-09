import { ImageResponse } from "next/og";

export const OG_SIZE = { width: 1200, height: 630 };

/** Social-preview card, drawn at build time. Only states facts that are true of the product. */
export function renderOgImage() {
  const ink = "#14181f";
  const paper = "#f2f2ee";
  const form = "#b73a18";
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: paper,
          color: ink,
          border: `12px solid ${ink}`,
          padding: "56px 64px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", fontSize: 40, fontWeight: 700, letterSpacing: 4, textTransform: "uppercase" }}>EcoTrace</div>
        <div style={{ display: "flex", height: 2, background: ink, marginTop: 20 }} />
        <div style={{ display: "flex", flex: 1, flexDirection: "column", justifyContent: "center" }}>
          <div style={{ display: "flex", fontSize: 92, fontWeight: 700, lineHeight: 1.0, maxWidth: 980 }}>
            A deforestation-risk score you can trace to its sources.
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 28 }}>
          <div style={{ display: "flex", width: 26, height: 26, background: form }} />
          <div style={{ display: "flex" }}>Trase · Forest 500 · Global Forest Watch · company sustainability pages</div>
        </div>
      </div>
    ),
    { ...OG_SIZE },
  );
}
