import { openHands } from "../open-hands-axios";
import type {
  CreateNotificationRequest,
  Notification,
  NotificationPage,
  NotificationPreferences,
  NotificationSettings,
  UpdateNotificationRequest,
} from "./notification-service.types";

/**
 * Notification service for managing notifications
 */
class NotificationService {
  /**
   * Get notifications for the current user
   */
  static async getNotifications(params?: {
    status?: string;
    notification_type?: string;
    limit?: number;
    page_id?: string;
  }): Promise<NotificationPage> {
    const { data } = await openHands.get<NotificationPage>(
      "/api/v1/notifications",
      { params },
    );
    return data;
  }

  /**
   * Get a single notification by ID
   */
  static async getNotification(notificationId: string): Promise<Notification> {
    const { data } = await openHands.get<Notification>(
      `/api/v1/notifications/${notificationId}`,
    );
    return data;
  }

  /**
   * Get unread notification count
   */
  static async getUnreadCount(): Promise<{ unread_count: number }> {
    const { data } = await openHands.get<{ unread_count: number }>(
      "/api/v1/notifications/unread-count",
    );
    return data;
  }

  /**
   * Create a new notification (internal use)
   */
  static async createNotification(
    request: CreateNotificationRequest,
  ): Promise<Notification> {
    const { data } = await openHands.post<Notification>(
      "/api/v1/notifications",
      request,
    );
    return data;
  }

  /**
   * Update a notification
   */
  static async updateNotification(
    notificationId: string,
    request: UpdateNotificationRequest,
  ): Promise<Notification> {
    const { data } = await openHands.patch<Notification>(
      `/api/v1/notifications/${notificationId}`,
      request,
    );
    return data;
  }

  /**
   * Delete a notification
   */
  static async deleteNotification(
    notificationId: string,
  ): Promise<{ deleted: boolean }> {
    const { data } = await openHands.delete<{ deleted: boolean }>(
      `/api/v1/notifications/${notificationId}`,
    );
    return data;
  }

  /**
   * Mark a notification as read
   */
  static async markAsRead(
    notificationId: string,
  ): Promise<Notification | null> {
    const { data } = await openHands.post<Notification | null>(
      `/api/v1/notifications/${notificationId}/mark-read`,
    );
    return data;
  }

  /**
   * Mark all notifications as read
   */
  static async markAllAsRead(): Promise<{ marked_count: number }> {
    const { data } = await openHands.post<{ marked_count: number }>(
      "/api/v1/notifications/mark-all-read",
    );
    return data;
  }

  /**
   * Get notification preferences
   */
  static async getPreferences(): Promise<NotificationPreferences> {
    const { data } = await openHands.get<NotificationPreferences>(
      "/api/v1/notifications/preferences",
    );
    return data;
  }

  /**
   * Update notification preferences
   */
  static async updatePreferences(
    settings: NotificationSettings,
  ): Promise<NotificationPreferences> {
    const { data } = await openHands.put<NotificationPreferences>(
      "/api/v1/notifications/preferences",
      settings,
    );
    return data;
  }
}

export default NotificationService;