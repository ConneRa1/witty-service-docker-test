import { useEffect, useCallback } from "react";
import { clearTextContent } from "#/components/features/chat/utils/chat-input.utils";

const isMac = typeof navigator !== "undefined" && /Mac|iPod|iPhone|iPad/.test(navigator.platform);

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  action: () => void;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target instanceof HTMLElement && e.target.isContentEditable)
      ) {
        return;
      }

      for (const shortcut of shortcuts) {
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = shortcut.ctrl ? e.ctrlKey : !e.ctrlKey;
        const metaMatch = shortcut.meta ? e.metaKey : !e.metaKey;
        const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey;

        if (keyMatch && ctrlMatch && metaMatch && shiftMatch) {
          e.preventDefault();
          shortcut.action();
          return;
        }
      }
    },
    [shortcuts],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}

export const MODIFIER_KEY = isMac ? "meta" : "ctrl";
export const MODIFIER_SYMBOL = isMac ? "⌘" : "Ctrl";

export const STOP_SHORTCUT: KeyboardShortcut = {
  key: "Escape",
  action: () => {
    window.dispatchEvent(new CustomEvent("chat-stop"));
  },
};

export function useClearInputShortcut(
  chatInputRef: React.RefObject<HTMLDivElement | null>,
) {
  const clearInput = useCallback(() => {
    if (chatInputRef.current) {
      clearTextContent(chatInputRef.current);
    }
  }, [chatInputRef]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        (e.key.toLowerCase() === "l" && (isMac ? e.metaKey : e.ctrlKey)) ||
        (e.key.toLowerCase() === "k" && (isMac ? e.metaKey : e.ctrlKey) && e.shiftKey)
      ) {
        if (
          document.activeElement instanceof HTMLInputElement ||
          document.activeElement instanceof HTMLTextAreaElement ||
          (document.activeElement instanceof HTMLElement &&
            document.activeElement.isContentEditable)
        ) {
          return;
        }
        e.preventDefault();
        clearInput();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [clearInput]);
}
