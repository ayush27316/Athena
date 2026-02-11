// import { AxiosError } from "axios"


export const getErrorMessages = (error: any): string[] => {
    // Check if it's an Axios-like error object (even if not an instance)
    const isAxiosError = error?.isAxiosError || error?.constructor?.name === 'AxiosError';

    if (isAxiosError || error?.request) {
        const data = error.response?.data;

        if (data?.errors && Array.isArray(data.errors)) {
            return data.errors;
        }
        if (data?.message) {
            return [data.message];
        }
        // TODO: this is not working
        // If there is a request but no response, the server is down
        if (error.request || error.code === 'ERR_CONNECTION_REFUSED') {
            return ["Server not responding. Please try again!"];
        }
    }

    if (error instanceof Error || error?.message) {
        return [error.message];
    }

    return ["An unknown error occurred."];
}

export const getInitials = (name: string): string => {
    return name
        .split(" ")
        .slice(0, 2)
        .map((word) => word[0])
        .join("")
        .toUpperCase()
}