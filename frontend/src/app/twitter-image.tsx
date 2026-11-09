import { renderOgImage } from "@/lib/ogImage";

export const alt = "EcoTrace: a deforestation-risk score you can trace to its sources";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return renderOgImage();
}
