import Sidebar from "@/components/sidebar";
import { ToastProvider } from "@/components/toast";
import { FlyoutProvider } from "@/components/info-flyout";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <FlyoutProvider>
        <div className="flex min-h-screen w-full bg-[#0A0A0F] text-[#E8E8F0] font-sans antialiased">
          <Sidebar />
          <main className="flex-1 min-w-0 flex flex-col">
            {children}
          </main>
        </div>
      </FlyoutProvider>
    </ToastProvider>
  );
}
