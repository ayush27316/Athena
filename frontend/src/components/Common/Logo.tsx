import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"
const logo = "/assets/images/logo.png";

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <img
          src={logo}
          alt="myProgress"
          className={cn(
            "h-15 w-auto group-data-[collapsible=icon]:hidden",
            className,
          )}
        />
        <img
          src={logo}
          alt="myProgress"
          className={cn(
            "size-5 hidden group-data-[collapsible=icon]:block",
            className,
          )}
        />
      </>
    ) : (
      <img
        src={logo}
        alt="myProgress"
        className={cn(variant === "full" ? "h-6 w-auto" : "size-5", className)}
      />
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
