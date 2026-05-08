import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";
import { CalendarIcon, FileText, Building2, CalendarDays, Coins, ShieldCheck, Crown, Users, CheckCircle2, Clock } from "lucide-react";
import { toast } from "sonner";
import { TopBar } from "@/components/everassist/TopBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/policy/new")({
  component: NewPolicyPage,
  head: () => ({
    meta: [
      { title: "New Policy Form · EverAssist" },
      { name: "description", content: "Create a new insurance policy record." },
    ],
  }),
});

const schema = z.object({
  policyNumber: z.string().min(1, "Required").max(64),
  riskReference: z.string().min(1, "Required").max(64),
  inceptionYear: z.coerce.number().int().min(1900).max(2100),
  insuredName: z.string().min(1, "Required").max(120),
  underwriterEmail: z.string().email("Invalid email").max(160),
  inceptionDate: z.date({ required_error: "Required" }),
  expiryDate: z.date({ required_error: "Required" }),
  currency: z.enum(["GBP", "USD", "EUR"]),
  placingType: z.enum(["OC", "DC", "FC"]),
  policyQuoteStatus: z.enum(["BOUND", "QUOTED", "REFERRED", "DECLINED"]),
  branchCode: z.enum(["E", "A", "B", "C"]),
  writtenLine: z.number().min(0).max(100),
  actualPremium: z.coerce.number().min(0),
  leadOrFollow: z.enum(["A", "F"]),
  sanctionsCheckComplete: z.enum(["Y", "N"]),
});

type PolicyForm = z.infer<typeof schema>;

function NewPolicyPage() {
  const navigate = useNavigate();
  const form = useForm<PolicyForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      policyNumber: "",
      riskReference: "",
      inceptionYear: new Date().getFullYear(),
      insuredName: "",
      underwriterEmail: "",
      currency: "GBP",
      placingType: "OC",
      policyQuoteStatus: "QUOTED",
      branchCode: "E",
      writtenLine: 100,
      actualPremium: 0,
      leadOrFollow: "A",
      sanctionsCheckComplete: "N",
    },
  });

  const onSubmit = async (values: PolicyForm) => {
    const payload = {
      ...values,
      inceptionDate: format(values.inceptionDate, "yyyy-MM-dd"),
      expiryDate: format(values.expiryDate, "yyyy-MM-dd"),
    };
    try {
      await fetch("/api/policy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch(() => null);
      toast.success("Policy submitted", {
        description: `Policy ${payload.policyNumber} created successfully.`,
      });
      form.reset();
    } catch {
      toast.error("Failed to submit policy");
    }
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden text-foreground">
      <div className="bg-grid flex h-full flex-1 flex-col overflow-hidden">
        <TopBar title="UnderWriting Intake" />
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl px-6 py-3">
            <div className="flex-1 min-w-0">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-0">
                <FormSection
                  icon={<Building2 className="h-4 w-4" />}
                  title="Identification"
                  description="Who and what this policy covers"
                >
                  <div className="grid grid-cols-1 gap-x-5 gap-y-2 md:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="policyNumber"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Policy Number</FormLabel>
                          <FormControl>
                            <Input placeholder="POL-00123" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="riskReference"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Risk Reference</FormLabel>
                          <FormControl>
                            <Input placeholder="RR-9981" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="inceptionYear"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Inception Year</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="2025" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="insuredName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Insured Name</FormLabel>
                          <FormControl>
                            <Input placeholder="Acme Holdings Ltd" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="underwriterEmail"
                      render={({ field }) => (
                        <FormItem className="md:col-span-2">
                          <FormLabel>Underwriter Email</FormLabel>
                          <FormControl>
                            <Input type="email" placeholder="name@company.com" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </FormSection>

                <FormSection
                  icon={<CalendarDays className="h-4 w-4" />}
                  title="Coverage period"
                  description="When the policy is in force"
                >
                  <div className="grid grid-cols-1 gap-x-5 gap-y-2 md:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="inceptionDate"
                      render={({ field }) => (
                        <FormItem className="flex flex-col">
                          <FormLabel>Inception Date</FormLabel>
                          <Popover>
                            <PopoverTrigger asChild>
                              <FormControl>
                                <Button
                                  variant="outline"
                                  className={cn(
                                    "justify-start text-left font-normal",
                                    !field.value && "text-muted-foreground"
                                  )}
                                >
                                  <CalendarIcon className="mr-2 h-4 w-4" />
                                  {field.value ? format(field.value, "PPP") : "Pick a date"}
                                </Button>
                              </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0" align="start">
                              <Calendar
                                mode="single"
                                selected={field.value}
                                onSelect={field.onChange}
                                initialFocus
                                className={cn("p-3 pointer-events-auto")}
                              />
                            </PopoverContent>
                          </Popover>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="expiryDate"
                      render={({ field }) => (
                        <FormItem className="flex flex-col">
                          <FormLabel>Expiry Date</FormLabel>
                          <Popover>
                            <PopoverTrigger asChild>
                              <FormControl>
                                <Button
                                  variant="outline"
                                  className={cn(
                                    "justify-start text-left font-normal",
                                    !field.value && "text-muted-foreground"
                                  )}
                                >
                                  <CalendarIcon className="mr-2 h-4 w-4" />
                                  {field.value ? format(field.value, "PPP") : "Pick a date"}
                                </Button>
                              </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0" align="start">
                              <Calendar
                                mode="single"
                                selected={field.value}
                                onSelect={field.onChange}
                                initialFocus
                                className={cn("p-3 pointer-events-auto")}
                              />
                            </PopoverContent>
                          </Popover>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </FormSection>

                <FormSection
                  icon={<Coins className="h-4 w-4" />}
                  title="Placement & financials"
                  description="Commercial terms and structure"
                >
                  <div className="grid grid-cols-1 gap-x-5 gap-y-2 md:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="placingType"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Placing Type</FormLabel>
                          <FormControl>
                            <SegmentedControl
                              value={field.value}
                              onChange={field.onChange}
                              options={[
                                { value: "OC", label: "Open Cover", accent: "primary" },
                                { value: "DC", label: "Declaration", accent: "primary" },
                                { value: "FC", label: "Facultative", accent: "primary" },
                              ]}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="policyQuoteStatus"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Quote Status</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="BOUND">BOUND</SelectItem>
                              <SelectItem value="QUOTED">QUOTED</SelectItem>
                              <SelectItem value="REFERRED">REFERRED</SelectItem>
                              <SelectItem value="DECLINED">DECLINED</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="branchCode"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Branch Code</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="E">E</SelectItem>
                              <SelectItem value="A">A</SelectItem>
                              <SelectItem value="B">B</SelectItem>
                              <SelectItem value="C">C</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="currency"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Currency</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="GBP">£ GBP</SelectItem>
                              <SelectItem value="USD">$ USD</SelectItem>
                              <SelectItem value="EUR">€ EUR</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="actualPremium"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Actual Premium</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                                {form.watch("currency") === "USD" ? "$" : form.watch("currency") === "EUR" ? "€" : "£"}
                              </span>
                              <Input
                                type="number"
                                min={0}
                                step="0.01"
                                placeholder="0.00"
                                className="pl-7"
                                {...field}
                                onChange={(e) => field.onChange(e.target.value)}
                              />
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="writtenLine"
                      render={({ field }) => (
                        <FormItem>
                          <div className="flex items-center justify-between">
                            <FormLabel>Written Line</FormLabel>
                            <span className="text-sm font-semibold tabular-nums text-foreground">
                              {field.value}%
                            </span>
                          </div>
                          <FormControl>
                            <Slider
                              min={0}
                              max={100}
                              step={1}
                              value={[field.value]}
                              onValueChange={(v) => field.onChange(v[0])}
                              className="pt-2"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </FormSection>

                <FormSection
                  icon={<ShieldCheck className="h-4 w-4" />}
                  title="Compliance & role"
                  description="Lead/follow position and sanctions clearance"
                >
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="leadOrFollow"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Lead or Follow</FormLabel>
                          <FormControl>
                            <SegmentedControl
                              value={field.value}
                              onChange={field.onChange}
                              options={[
                                { value: "A", label: "Lead", icon: <Crown className="h-3.5 w-3.5" />, accent: "primary" },
                                { value: "F", label: "Follow", icon: <Users className="h-3.5 w-3.5" />, accent: "muted" },
                              ]}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="sanctionsCheckComplete"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Sanctions Check</FormLabel>
                          <FormControl>
                            <SegmentedControl
                              value={field.value}
                              onChange={field.onChange}
                              options={[
                                { value: "Y", label: "Complete", icon: <CheckCircle2 className="h-3.5 w-3.5" />, accent: "success" },
                                { value: "N", label: "Pending", icon: <Clock className="h-3.5 w-3.5" />, accent: "warning" },
                              ]}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </FormSection>

                <div className="sticky bottom-0 -mx-6 flex items-center justify-end gap-2 border-t border-border/60 bg-background/80 px-6 py-2 backdrop-blur">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => navigate({ to: "/" })}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={form.formState.isSubmitting} className="min-w-32">
                    {form.formState.isSubmitting ? "Submitting…" : "Submit Policy"}
                  </Button>
                </div>
              </form>
            </Form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FormSection({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-x border-t border-border/60 bg-card last:border-b first:rounded-t-xl last:rounded-b-xl">
      <header className="flex items-center gap-2.5 border-b border-border/60 px-4 py-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <h2 className="text-xs font-semibold leading-none">{title}</h2>
          {description && (
            <p className="mt-0.5 text-[11px] text-muted-foreground">{description}</p>
          )}
        </div>
      </header>
      <div className="px-4 py-2.5">{children}</div>
    </section>
  );
}

const ACCENT_STYLES = {
  primary: {
    active: "border-primary bg-primary/10 text-primary ring-2 ring-primary/30",
    icon: "bg-primary text-primary-foreground",
  },
  success: {
    active: "border-emerald-500 bg-emerald-50 text-emerald-700 ring-2 ring-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-400",
    icon: "bg-emerald-500 text-white",
  },
  warning: {
    active: "border-amber-500 bg-amber-50 text-amber-800 ring-2 ring-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300",
    icon: "bg-amber-500 text-white",
  },
  muted: {
    active: "border-foreground/40 bg-muted text-foreground ring-2 ring-foreground/15",
    icon: "bg-foreground text-background",
  },
} as const;

function SegmentOption({
  active,
  onClick,
  icon,
  title,
  subtitle,
  accent,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  accent: keyof typeof ACCENT_STYLES;
}) {
  const styles = ACCENT_STYLES[accent];
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={cn(
        "group relative flex items-center gap-3 rounded-lg border-2 border-border/60 bg-card px-3 py-2.5 text-left transition-all duration-200",
        "hover:border-foreground/30 hover:shadow-sm",
        active ? styles.active : "text-muted-foreground"
      )}
    >
      <span
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-all duration-200",
          active ? styles.icon : "bg-muted text-muted-foreground group-hover:scale-105"
        )}
      >
        {icon}
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="text-sm font-semibold leading-tight">{title}</span>
        <span className="text-[11px] leading-tight opacity-70">{subtitle}</span>
      </span>
      <span
        className={cn(
          "ml-auto h-3 w-3 shrink-0 rounded-full border-2 transition-all duration-200",
          active
            ? "border-current bg-current shadow-[0_0_0_3px_hsl(var(--background)),0_0_0_4px_currentColor]"
            : "border-border"
        )}
      />
    </button>
  );
}

const SEG_ACCENT = {
  primary: "bg-primary text-primary-foreground shadow-sm",
  success: "bg-emerald-500 text-white shadow-sm",
  warning: "bg-amber-500 text-white shadow-sm",
  muted: "bg-foreground text-background shadow-sm",
} as const;

type SegOption<T extends string> = {
  value: T;
  label: string;
  icon?: React.ReactNode;
  accent: keyof typeof SEG_ACCENT;
};

function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: SegOption<T>[];
}) {
  return (
    <div
      role="radiogroup"
      className="inline-flex h-9 w-full rounded-lg border border-border bg-muted/50 p-0.5"
    >
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "relative flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-all duration-200",
              active
                ? SEG_ACCENT[opt.accent]
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {opt.icon}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
