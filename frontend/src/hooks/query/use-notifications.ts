import { useQuery } from "@tanstack/react-query";
import NotificationService from "#/api/notification-service/notification-service.api";
import type { Notification, NotificationPage } from "#/api/notification-service/notification-service.types";

interface UseNotificationsOptions {
  status?: string;
  notificationType?: string;
  limit?: number;
  pageId?: string;
}

const getNotificationsQueryFn = async ({
  status,
  notificationType,
  limit,
  pageId,
}: UseNotificationsOptions): Promise<NotificationPage> => {
  return NotificationService.getNotifications({
    status,
    notification_type: notificationType,
    limit,
    page_id: pageId,
  });
};

export const useNotifications = (options: UseNotificationsOptions = {}) => {
  const { status, notificationType, limit = 50, pageId } = options;

  return useQuery({
    queryKey: ["notifications", { status, notificationType, limit, pageId }],
    queryFn: () =>
      getNotificationsQueryFn({ status, notificationType, limit, pageId }),
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
  });
};

export const useUnreadNotificationCount = () => {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => NotificationService.getUnreadCount(),
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 30, // Poll every 30 seconds
  });
};

export const useNotification = (notificationId: string) => {
  return useQuery({
    queryKey: ["notifications", notificationId],
    queryFn: () => NotificationService.getNotification(notificationId),
    enabled: !!notificationId,
  });
};