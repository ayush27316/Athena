import { createFileRoute, Link } from "@tanstack/react-router"
import { BookOpen, Briefcase, FileCode, UserCog, Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: DashboardPage,
})

function DashboardPage() {
  const { isAdmin } = useAuth()

  const quickActions = [
    {
      title: "Audit Report",
      description: "View student degree audit reports",
      icon: BookOpen,
      path: "/audit",
      color: "text-blue-600",
    },
    {
      title: "Student Management",
      description: "Manage student records",
      icon: Users,
      path: "/students",
      color: "text-green-600",
    },
    {
      title: "Block Management",
      description: "Manage degree blocks and requirements",
      icon: Briefcase,
      path: "/blocks",
      color: "text-purple-600",
    },
    {
      title: "Editor",
      description: "Edit scribe code for blocks",
      icon: FileCode,
      path: "/editor",
      color: "text-orange-600",
    },
  ]

  const adminActions = [
    {
      title: "Operator Management",
      description: "Manage system operators",
      icon: UserCog,
      path: "/operators",
      color: "text-red-600",
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Welcome to oneAdvisor - Your degree audit management system
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {quickActions.map((action) => (
          <Card key={action.path} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3">
                <action.icon className={`h-6 w-6 ${action.color}`} />
                <CardTitle className="text-lg">{action.title}</CardTitle>
              </div>
              <CardDescription>{action.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Link to={action.path}>
                <Button variant="outline" className="w-full">
                  Go to {action.title}
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}

        {isAdmin &&
          adminActions.map((action) => (
            <Card
              key={action.path}
              className="hover:shadow-lg transition-shadow"
            >
              <CardHeader>
                <div className="flex items-center gap-3">
                  <action.icon className={`h-6 w-6 ${action.color}`} />
                  <CardTitle className="text-lg">{action.title}</CardTitle>
                </div>
                <CardDescription>{action.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Link to={action.path}>
                  <Button variant="outline" className="w-full">
                    Go to {action.title}
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  )
}
