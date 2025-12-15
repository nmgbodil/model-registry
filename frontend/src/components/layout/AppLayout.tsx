import { ReactNode } from "react";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { SrAnnouncer } from "@/components/SrAnnouncer";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <SidebarProvider>
      {/* Screen reader announcer for dynamic content */}
      <SrAnnouncer />
      
      {/* Skip navigation link for keyboard users - WCAG 2.4.1 */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <div className="flex min-h-screen w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col">
          <header 
            role="banner"
            className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-4"
          >
            <SidebarTrigger 
              className="-ml-1" 
              aria-label="Toggle sidebar navigation"
            />
          </header>
          <main 
            id="main-content" 
            role="main"
            tabIndex={-1}
            className="flex-1 p-6 focus:outline-none"
          >
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
