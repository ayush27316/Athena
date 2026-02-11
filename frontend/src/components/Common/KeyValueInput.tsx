import { Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export interface KeyValueInputProps {
    label?: string
    attributes: Record<string, string>
    onChange: (attributes: Record<string, string>) => void
    isViewMode?: boolean
    keyPlaceholder?: string
    valuePlaceholder?: string
    maxHeight?: string
}

export function KeyValueInput({
    label = "Attributes",
    attributes,
    onChange,
    isViewMode = false,
    keyPlaceholder = "Key",
    valuePlaceholder = "Value",
    maxHeight = "150px",
}: KeyValueInputProps) {
    const [newKey, setNewKey] = useState("")
    const [newValue, setNewValue] = useState("")

    const addAttribute = () => {
        if (!newKey) return
        onChange({
            ...attributes,
            [newKey]: newValue,
        })
        setNewKey("")
        setNewValue("")
    }

    const removeAttribute = (key: string) => {
        const newAttrs = { ...attributes }
        delete newAttrs[key]
        onChange(newAttrs)
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            e.preventDefault()
            addAttribute()
        }
    }

    return (
        <div className="space-y-4">
            {!isViewMode && (
                <div className="space-y-1">
                    <div className="grid grid-cols-[1fr_1fr_40px] items-end gap-2">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">{label}</Label>
                            <Input
                                value={newKey}
                                onChange={(e) => setNewKey(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={keyPlaceholder}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium invisible">Value</Label>
                            <Input
                                value={newValue}
                                onChange={(e) => setNewValue(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={valuePlaceholder}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium invisible">Add</Label>
                            <Button
                                type="button"
                                onClick={addAttribute}
                                size="sm"
                                variant="secondary"
                                className="h-9 w-9 p-0"
                            >
                                <Plus className="h-3 w-3" />
                            </Button>
                        </div>
                    </div>
                </div>
            )}
            {isViewMode && Object.keys(attributes).length > 0 && (
                <Label className="text-sm font-medium">{label}</Label>
            )}
            <div
                className="flex flex-wrap gap-2 overflow-y-auto"
                style={{ maxHeight }}
            >
                {Object.entries(attributes).map(([key, value]) => (
                    <div
                        key={key}
                        className="flex gap-2 items-center bg-muted/50 border p-2.5 rounded-sm text-xs w-fit"
                    >
                        <div className="min-w-0">
                            <span className="block text-[10px] text-muted-foreground font-mono truncate">
                                {key}
                            </span>
                            <span className="block font-medium truncate">
                                {value as string}
                            </span>
                        </div>
                        {!isViewMode && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-muted"
                                onClick={() => removeAttribute(key)}
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                        )}
                    </div>
                ))}
            </div>
            {Object.keys(attributes).length === 0 && isViewMode && (
                <div className="text-xs text-muted-foreground italic text-center py-3 border rounded border-dashed">
                    No {label.toLowerCase()}
                </div>
            )}
        </div>
    )
}
