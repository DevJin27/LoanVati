import type { PropsWithChildren } from "react";
import { X } from "lucide-react";

interface ModalProps {
  title: string;
  open: boolean;
  onClose: () => void;
}

export function Modal({ title, open, onClose, children }: PropsWithChildren<ModalProps>): JSX.Element | null {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-medium text-gray-900">{title}</h2>
          <button className="rounded p-1 text-gray-500 hover:bg-gray-100" type="button" onClick={onClose} aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
