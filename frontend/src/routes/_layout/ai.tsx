import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { OneAdvisorService } from "@/client/sdk.gen"
import type { AiResponse } from "@/client/types.gen"

export const Route = createFileRoute("/_layout/ai")({
    component: AIPlaygroundPage,
})

function AIPlaygroundPage() {
    const [prompt, setPrompt] = useState("")
    const [response, setResponse] = useState<AiResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const service = new OneAdvisorService()

    const handleGenerate = async () => {
        if (!prompt.trim()) return
        setLoading(true)
        setError(null)
        setResponse(null)

        try {
            const res = await service.operation2({
                body: { prompt },
            })
            setResponse(res.data as AiResponse)
        } catch (err: unknown) {
            const message =
                err instanceof Error ? err.message : "Something went wrong"
            setError(message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">AI Playground</h1>
                <p className="text-muted-foreground mt-2">
                    Test the xAI Grok text generation endpoint
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Generate</CardTitle>
                    <CardDescription>
                        Enter a prompt and get a structured AI response with confidence
                        scoring.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <textarea
                        id="ai-prompt"
                        className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-y"
                        placeholder="Ask anything... Try 'How many words are in this sentence?' or 'What time is it?'"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                                handleGenerate()
                            }
                        }}
                    />
                    <div className="flex items-center gap-3">
                        <Button
                            id="ai-generate-btn"
                            onClick={handleGenerate}
                            disabled={loading || !prompt.trim()}
                        >
                            {loading ? (
                                <span className="flex items-center gap-2">
                                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                                    Generating…
                                </span>
                            ) : (
                                "Generate"
                            )}
                        </Button>
                        <span className="text-xs text-muted-foreground">
                            ⌘+Enter to submit
                        </span>
                    </div>
                </CardContent>
            </Card>

            {error && (
                <Card className="border-destructive">
                    <CardContent className="pt-6">
                        <p className="text-destructive text-sm font-medium">{error}</p>
                    </CardContent>
                </Card>
            )}

            {response && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                            <span>Response</span>
                            <span
                                className={`text-sm font-normal px-2.5 py-0.5 rounded-full ${response.confidence >= 0.8
                                    ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                                    : response.confidence >= 0.5
                                        ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                                        : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                                    }`}
                            >
                                Confidence: {(response.confidence * 100).toFixed(0)}%
                            </span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <h4 className="text-sm font-medium text-muted-foreground mb-1">
                                Answer
                            </h4>
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                {response.answer}
                            </p>
                        </div>

                        {response.sources && response.sources.length > 0 && (
                            <div>
                                <h4 className="text-sm font-medium text-muted-foreground mb-1">
                                    Sources
                                </h4>
                                <ul className="list-disc list-inside text-sm text-muted-foreground">
                                    {response.sources.map((src, i) => (
                                        <li key={i}>{src}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
