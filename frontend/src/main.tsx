import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import "./lib/api-client"
import { routeTree } from "./routeTree.gen"
import { AxiosError } from "axios"
import { getErrorMessages } from "./utils"
import { toast } from "sonner"

const handleApiError = (error: unknown) => {
  if (error instanceof AxiosError && [401, 403].includes(error.response?.status ?? 0)) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    return
  }

  const messages = getErrorMessages(error)

  messages.forEach((msg) => {
    toast.error("Something went wrong!", {
      description: msg,
    })
  })
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
