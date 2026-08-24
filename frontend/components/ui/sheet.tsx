"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { useReturnFocus } from "@/lib/ui/use-return-focus";

/**
 * A panel for secondary controls and contextual help
 * (docs/02_UX_UI_SPEC.md sections 12 and 15).
 *
 * Bottom sheet on small screens, side panel from `md` up, so opening help
 * never loses the user's place. Focus trapping, escape-to-close, scroll lock
 * and `aria-modal` come from the underlying dialog primitive.
 */
export type SheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** Linked as the accessible description. */
  description?: string;
  /** Sticky action row at the bottom of the sheet. */
  footer?: ReactNode;
  children: ReactNode;
};

export function Sheet({ open, onOpenChange, title, description, footer, children }: SheetProps) {
  const onCloseAutoFocus = useReturnFocus(open);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            "fixed inset-0 z-40 bg-primary/25",
            "data-[state=open]:animate-in data-[state=open]:fade-in",
          )}
        />
        <Dialog.Content
          onCloseAutoFocus={onCloseAutoFocus}
          className={cn(
            "fixed z-50 flex flex-col bg-surface shadow-overlay",
            "transition-transform duration-base ease-standard",
            // Mobile: bottom sheet, capped so the page stays visible behind it.
            "inset-x-0 bottom-0 max-h-[85vh] rounded-t-sheet",
            // Desktop: right-hand panel.
            "md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[420px]",
            "md:rounded-l-sheet md:rounded-tr-none",
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b border-border p-5">
            <div className="flex flex-col gap-1">
              <Dialog.Title className="text-h3 font-medium text-primary">{title}</Dialog.Title>
              {description ? (
                <Dialog.Description className="text-support text-secondary">
                  {description}
                </Dialog.Description>
              ) : null}
            </div>
            <Dialog.Close
              className={cn(
                "-m-2 flex size-touch shrink-0 items-center justify-center rounded-control",
                "text-secondary transition-colors duration-fast hover:bg-bg hover:text-primary",
              )}
            >
              <X className="size-5" aria-hidden="true" />
              <span className="sr-only">Close</span>
            </Dialog.Close>
          </div>

          <div className="flex-1 overflow-y-auto p-5">{children}</div>

          {footer ? <div className="border-t border-border p-5">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
