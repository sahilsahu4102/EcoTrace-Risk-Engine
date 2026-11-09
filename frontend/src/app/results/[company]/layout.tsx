import type { Metadata } from "next";

export async function generateMetadata({ params }: { params: Promise<{ company: string }> }): Promise<Metadata> {
  const { company } = await params;
  const name = decodeURIComponent(company);
  return {
    title: `${name} deforestation risk`,
    description: `Deforestation-risk assessment for ${name}, with the evidence behind the score.`,
    robots: { index: false },
  };
}

export default function ResultsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
