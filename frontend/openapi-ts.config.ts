import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
    input: "./openapi.json",
    output: "./src/client",

    plugins: [
        "@hey-api/client-axios",
        {
            name: "@hey-api/sdk",
            operations: {
                // TODO: this configuration was suggested by an ai
                // need to check if it makes sense. Previously they
                //       asClass: true
                //       operationId: true
                strategy: "single",
                nesting: "operationId",
                containerName: "OneAdvisorService",
                methodName: (operation) => {
                    // @ts-expect-error
                    let name: string = operation.name
                    // @ts-expect-error
                    const service: string = operation.service

                    if (!name || typeof name !== "string") {
                        return "operation"
                    }

                    if (service && name.toLowerCase().startsWith(service.toLowerCase())) {
                        name = name.slice(service.length)
                    }

                    return name.charAt(0).toLowerCase() + name.slice(1)
                },
            },
        },
        {
            name: "@hey-api/schemas",
            type: "json",
        },
    ],
})
