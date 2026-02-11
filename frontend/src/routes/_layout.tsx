import { createFileRoute, Outlet } from "@tanstack/react-router"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  // Authentication check removed - all routes are now publicly accessible
})

function LayoutContent() {

  return (
    <SidebarInset
      className={cn("bg-sidebar h-screen overflow-hidden w-screen flex-none peer-data-[variant=inset]:min-h-[calc(100svh-theme(spacing.4))] md:peer-data-[variant=inset]:rounded-none md:peer-data-[variant=inset]:shadow-none")}
    >
      <div className="bg-background mr-4 rounded-t-3xl h-full flex flex-col shadow-lg relative overflow-hidden overscroll-none">
        {/* Fixed Elements */}
        <div className="absolute top-0 left-0 right-0 h-2 z-40 bg-gradient-to-b from-background/90 to-transparent backdrop-blur-[0.5px] pointer-events-none" />
        <SidebarTrigger className="absolute top-4 left-4 z-50 text-muted-foreground" />

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto pl-10 pt-16 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] overscroll-none flex flex-col">
          <main className="flex-1 bg-background flex flex-col">
            <div className="mx-auto max-w-7xl w-full flex-1 flex flex-col">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </SidebarInset>
  )
}

function Layout() {
  return (
    <SidebarProvider className="bg-sidebar overflow-x-hidden">
      <AppSidebar />
      <LayoutContent />
    </SidebarProvider>
  )
}

export default Layout
