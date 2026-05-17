import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useWebSocket, WebSocketHookOptions } from "#/hooks/use-websocket";
import type { Notification } from "#/api/notification-service/notification-service.types";

interface UseNotificationWebSocketOptions extends WebSocketHookOptions {
  enabled?: boolean;
}

export const useNotificationWebSocket = (
  options: UseNotificationWebSocketOptions = {},
) => {
  const { enabled = true, onMessage, ...wsOptions } = options;
  const queryClient = useQueryClient();

  const handleMessage = React.useCallback(
    (event: MessageEvent) => {
      try {
        const notification: Notification = JSON.parse(event.data);
        queryClient.invalidateQueries({ queryKey: ["notifications"] });
        onMessage?.(event);
      } catch (error) {
        console.error("Failed to parse notification:", error);
      }
    },
    [queryClient, onMessage],
  );

  const wsUrl = "/ws/notifications";

  const ws = useWebSocket<Notification>(wsUrl, {
    ...wsOptions,
    onMessage: handleMessage,
    enabled,
  });

  return ws;
};

export const useNotificationSound = () => {
  const audioRef = React.useRef<HTMLAudioElement | null>(null);

  React.useEffect(() => {
    audioRef.current = new Audio("/beep.wav");
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const playSound = React.useCallback(() => {
    if (audioRef.current) {
      audioRef.current.play().catch(() => {
        // Ignore autoplay errors
      });
    }
  }, []);

  return { playSound };
};
