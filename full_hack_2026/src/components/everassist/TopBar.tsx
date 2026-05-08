import { Bell, LayoutDashboard, Menu, Plus, Sparkles, FileText } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function TopBar({ onNewRequirement, title }: { onNewRequirement?: () => void; title?: string }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-12 max-w-[1600px] items-center justify-between px-4 relative">
        {title && (
          <span className="absolute left-1/2 -translate-x-1/2 text-2xl font-bold tracking-tight pointer-events-none">
            {title}
          </span>
        )}
        <Link
          to="/"
          aria-label="Go to home"
          className="flex items-center gap-3 rounded-lg outline-none transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-purple/50"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-purple to-cyan shadow-glow-purple">
            <Sparkles className="h-4 w-4 text-background" strokeWidth={2.5} />
          </div>
          <div className="font-display text-lg font-semibold tracking-tight">
            Highline<span className="text-gradient-purple">Hub</span>
          </div>
          <span className="ml-2 hidden rounded-full border border-border/60 bg-surface-elevated px-2 py-0.5 font-mono text-[10px] tracking-widest text-muted-foreground sm:inline-flex">
            v1.0
          </span>
        </Link>

        <div className="flex items-center gap-2">
          {onNewRequirement && (
            <Button
              onClick={onNewRequirement}
              size="sm"
              className="h-8 gap-1.5 rounded-lg px-3 text-xs font-semibold"
            >
              <Plus className="h-3.5 w-3.5" />
              New Requirement
            </Button>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-lg border border-border/60 bg-surface-elevated hover:border-purple/40"
                aria-label="Menu"
              >
                <Menu className="h-4 w-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem asChild>
                <Link to="/" className="flex cursor-pointer items-center gap-2">
                  <LayoutDashboard className="h-4 w-4" />
                  Dashboard
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel className="text-xs uppercase tracking-wider text-muted-foreground">
                Policy
              </DropdownMenuLabel>
              <DropdownMenuItem asChild>
                <Link to="/policy/new" className="flex cursor-pointer items-center gap-2">
                  <FileText className="h-4 w-4" />
                  New Policy
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            variant="ghost"
            size="icon"
            className="relative h-8 w-8 rounded-lg border border-border/60 bg-surface-elevated hover:border-purple/40"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4 text-muted-foreground" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-cyan" />
          </Button>

          <Button
            variant="ghost"
            className="h-8 rounded-lg border border-border/60 bg-surface-elevated px-1.5 hover:border-purple/40"
            aria-label="User profile"
          >
            <Avatar className="h-6 w-6 border border-border/60">
              <AvatarImage src="https://randomuser.me/api/portraits/women/44.jpg" alt="User" />
              <AvatarFallback className="bg-gradient-to-br from-purple/90 to-cyan/90 text-[10px] font-semibold text-background">
                AR
              </AvatarFallback>
            </Avatar>
          </Button>
        </div>
      </div>
    </header>
  );
}
