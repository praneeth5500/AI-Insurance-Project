"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { useReturnFocus } from "@/lib/ui/use-return-focus";

/**
 * A centred dialog for a decision that must be resolved before continuing.
 *
 * Prefer `Sheet` for contextual help and secondary controls; a modal
 * interrupts, so it should be rare.
 */
export type ModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  footer?: ReactNode;
  children?: ReactNode;
};

export function Modal({ open, onOpenChange, title, description, footer, children }: ModalProps) {
  const onCloseAutoFocus = useReturnFocus(open);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-primary/25" />
        <Dialog.Content
          onCloseAutoFocus={onCloseAutoFocus}
          className={cn(
            "fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-[480px]",
            "-translate-x-1/2 -translate-y-1/2",
            "rounded-card bg-surface shadow-overlay",
            "max-h-[85vh] overflow-y-auto",
          )}
        >
          <div className="flex items-start justify-between gap-4 p-5 pb-0">
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

          {children ? <div className="p-5">{children}</div> : null}

          {footer ? (
            <div className="flex flex-col-reverse gap-2 p-5 pt-0 sm:flex-row sm:justify-end">
              {footer}
            </div>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
