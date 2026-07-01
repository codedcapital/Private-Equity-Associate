import { Suspense } from "react";
import AppLayout from "@/components/app-layout";
import DealPage from "./deal-page";

export const dynamic = "force-dynamic";

interface DealPageProps {
  params: Promise<{ id: string }>;
}

async function DealContent({ params }: DealPageProps) {
  const { id } = await params;
  return <DealPage id={id} />;
}

export default function Deal({ params }: DealPageProps) {
  return (
    <AppLayout>
      <Suspense fallback={<div className="p-5 text-[#6B7280]">Loading deal…</div>}>
        <DealContent params={params} />
      </Suspense>
    </AppLayout>
  );
}
