import {
  BookOpen,
  Briefcase,
  Home,
  Sparkles,
  UserCog,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: BookOpen, title: "Audit", path: "/audit" },
  { icon: Users, title: "Students", path: "/students" },
  { icon: Briefcase, title: "Blocks", path: "/blocks" },
  { icon: Sparkles, title: "AI", path: "/ai" },
]

const adminItems: Item[] = [
  ...baseItems,
  { icon: UserCog, title: "Operators", path: "/operators" },
]


export function AppSidebar() {
  const { user: currentUser } = useAuth()

  var items = currentUser?.role === "admin" ? adminItems : baseItems

  return (
    <Sidebar collapsible="offcanvas" variant="inset" className="p-0">
      <SidebarHeader className="px-4 py-6 flex flex-row items-center gap-2">
        <Logo variant="responsive" />
        <span className="italic font-medium">myProgress</span>
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
