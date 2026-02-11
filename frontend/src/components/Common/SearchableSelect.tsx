"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import {
    Combobox,
    ComboboxContent,
    ComboboxEmpty,
    ComboboxInput,
    ComboboxItem,
    ComboboxList,
    ComboboxTrigger,
    ComboboxValue,
} from "@/components/ui/combobox"

export interface SearchableSelectOption {
    value: string
    label: string
}

interface SearchableSelectProps {
    options: SearchableSelectOption[]
    value?: string
    onChange: (value: string) => void
    placeholder?: string
    emptyMessage?: string
    disabled?: boolean
    className?: string
}

export function SearchableSelect({
    options,
    value,
    onChange,
    placeholder = "Select option...",
    emptyMessage = "No option found.",
    disabled = false,
    className,
}: SearchableSelectProps) {
    const selectedOption = options.find((option) => option.value === value)

    // Create a default option for the placeholder
    const defaultOption = { value: "", label: placeholder }
    const currentValue = selectedOption || defaultOption

    return (
        <Combobox
            items={options}
            value={currentValue}
            onValueChange={(item) => {
                if (item) {
                    onChange(item.value)
                }
            }}
        >
            <ComboboxTrigger
                render={
                    <Button
                        variant="outline"
                        className={`w-full justify-between ${!selectedOption ? "text-muted-foreground" : ""} ${className || ''}`}
                        disabled={disabled}
                    >
                        <ComboboxValue />
                    </Button>
                }
            />
            <ComboboxContent>
                <ComboboxInput showTrigger={false} placeholder={placeholder} />
                <ComboboxEmpty>{emptyMessage}</ComboboxEmpty>
                <ComboboxList>
                    {(item) => (
                        <ComboboxItem key={item.value} value={item}>
                            {item.label}
                        </ComboboxItem>
                    )}
                </ComboboxList>
            </ComboboxContent>
        </Combobox>
    )
}
