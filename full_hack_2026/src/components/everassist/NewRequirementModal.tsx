import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { requirements, type Priority, type RequirementStatus } from "@/lib/requirements-data";

const LOB_OPTIONS = ["Motor LoB", "Home LoB", "DevOps", "Engineering", "QA", "All LoB"];
const SOURCE_OPTIONS = ["EverAssist", "GitHub Copilot", "Copilot", "Manual"];
const PRIORITY_OPTIONS: Priority[] = ["High", "Med", "Low"];

function deriveInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2);
}

function nextId(): string {
  const nums = requirements
    .map((r) => parseInt(r.id.replace("US-", ""), 10))
    .filter((n) => !isNaN(n));
  const max = nums.length ? Math.max(...nums) : 0;
  return `US-${String(max + 1).padStart(3, "0")}`;
}

export function NewRequirementModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [lob, setLob] = useState("");
  const [source, setSource] = useState("");
  const [priority, setPriority] = useState<Priority | "">("");
  const [ownerName, setOwnerName] = useState("");
  const [tags, setTags] = useState("");
  const [error, setError] = useState("");

  const reset = () => {
    setTitle("");
    setLob("");
    setSource("");
    setPriority("");
    setOwnerName("");
    setTags("");
    setError("");
  };

  const handleSubmit = () => {
    if (!title.trim() || !lob || !source || !priority || !ownerName.trim()) {
      setError("Please fill in all required fields.");
      return;
    }
    const id = nextId();
    requirements.push({
      id,
      title: title.trim(),
      lob,
      source,
      status: "in-progress" as RequirementStatus,
      priority: priority as Priority,
      owner: { initials: deriveInitials(ownerName), name: ownerName.trim() },
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      stages: ["active", "pending", "pending", "pending", "pending", "pending"],
    });
    reset();
    onOpenChange(false);
    navigate({ to: "/requirement/$id", params: { id } });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            New Requirement
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="space-y-1.5">
            <Label htmlFor="req-title">
              Title <span className="text-destructive">*</span>
            </Label>
            <Input
              id="req-title"
              placeholder="Describe the requirement..."
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setError("");
              }}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>
                Line of Business <span className="text-destructive">*</span>
              </Label>
              <Select
                value={lob}
                onValueChange={(v) => {
                  setLob(v);
                  setError("");
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select LOB" />
                </SelectTrigger>
                <SelectContent>
                  {LOB_OPTIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>
                Priority <span className="text-destructive">*</span>
              </Label>
              <Select
                value={priority}
                onValueChange={(v) => {
                  setPriority(v as Priority);
                  setError("");
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select" />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITY_OPTIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>
              Source <span className="text-destructive">*</span>
            </Label>
            <Select
              value={source}
              onValueChange={(v) => {
                setSource(v);
                setError("");
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select source" />
              </SelectTrigger>
              <SelectContent>
                {SOURCE_OPTIONS.map((o) => (
                  <SelectItem key={o} value={o}>
                    {o}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="req-owner">
              Owner <span className="text-destructive">*</span>
            </Label>
            <Input
              id="req-owner"
              placeholder="Full name"
              value={ownerName}
              onChange={(e) => {
                setOwnerName(e.target.value);
                setError("");
              }}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="req-tags">
              Tags{" "}
              <span className="text-xs text-muted-foreground">(comma-separated)</span>
            </Label>
            <Input
              id="req-tags"
              placeholder="QA, EverAssist, ..."
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => {
              reset();
              onOpenChange(false);
            }}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit}>Create Requirement</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
