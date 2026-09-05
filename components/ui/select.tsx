import * as React from "react";
import { cn } from "@/lib/utils";

const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<"select">>(({ className, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "flex min-h-11 w-full appearance-none rounded-md border border-input bg-card px-3 py-2 text-base text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring md:text-sm",
      className,
    )}
    {...props}
  />
));
Select.displayName = "Select";

export { Select };
