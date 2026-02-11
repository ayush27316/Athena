/**
 * API Client Configuration
 * Sets up the hey-api client with base URL and authentication
 */
import { client } from "@/client/client.gen"

// Configure the client
export function configureClient() {
    const baseURL = import.meta.env.VITE_API_URL || ""

    client.setConfig({
        baseURL,
        // Provide the auth token for Bearer authentication
        auth: () => {
            const token = localStorage.getItem("access_token")
            return token || undefined
        },
    })
}

// Initialize client on module load
configureClient()

export { client }
