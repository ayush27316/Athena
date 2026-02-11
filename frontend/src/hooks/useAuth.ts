import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import { OneAdvisorService } from "@/client"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

export interface UserProfile {
  id: string
  email: string
  full_name?: string | null
  role: "admin" | "operator" | "coder"
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  // instantiate the service
  const service = new OneAdvisorService()

  const { data: user, isLoading: isLoadingUser } = useQuery<
    UserProfile | null,
    Error
  >({
    queryKey: ["currentUser"],
    queryFn: async () => {
      const token = localStorage.getItem("access_token")
      if (!token) return null

      try {
        // Pass the token in the headers for this request
        const response = await service.authReadUsersMe()

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const data = response.data as any

        // Handle the wrapped response format if existing backend wraps it
        if (data?.success) {
          return data.content as UserProfile
        }

        // Fallback if the response is the user object itself (api change possibility)
        if (data?.email && data?.role) {
          return data as UserProfile
        }

        return null
      } catch (_e) {
        // Token invalid, clear it
        localStorage.removeItem("access_token")
        return null
      }
    },
    enabled: isLoggedIn(),
    staleTime: 30 * 60 * 1000, // 30 minutes
  })

  const login = async (data: { username: string; password: string }) => {
    const response = await service.authLogin({
      body: {
        username: data.username,
        password: data.password,
      },
    })

    if (response.data?.access_token) {
      localStorage.setItem("access_token", response.data.access_token)
    } else {
      throw new Error("Login failed")
    }
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      navigate({ to: "/" })
    },
    onError: (error: Error) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const err = error as any
      const message =
        err?.response?.data?.detail || err?.message || "Login failed"
      showErrorToast(message)
    },
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    queryClient.clear()
    navigate({ to: "/login" })
  }

  const isAdmin = user?.role === "admin"

  return {
    loginMutation,
    logout,
    user,
    isLoadingUser,
    isAdmin,
  }
}

export { isLoggedIn }
export default useAuth
