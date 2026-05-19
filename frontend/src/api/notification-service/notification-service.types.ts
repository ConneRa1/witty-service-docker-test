export const NotificationType = {
  TASK_COMPLETED: "TASK_COMPLETED",
  TASK_FAILED: "TASK_FAILED",
  TASK_STARTED: "TASK_STARTED",
  LONG_RUNNING_WARNING: "LONG_RUNNING_WARNING",
  SECURITY_ALERT: "SECURITY_ALERT",
  SYSTEM_MESSAGE: "SYSTEM_MESSAGE",
  USER_MESSAGE: "USER_MESSAGE",
  CONVERSATION_SHARED: "CONVERSATION_SHARED",
  MENTION: "MENTION",
} as const;

export type NotificationType = (typeof NotificationType)[keyof typeof NotificationType];

export const NotificationPriority = {
  LOW: "LOW",
  NORMAL: "NORMAL",
  HIGH: "HIGH",
  URGENT: "URGENT",
} as const;

export type NotificationPriority =
  (typeof NotificationPriority)[keyof typeof NotificationPriority];

export const NotificationStatus = {
  UNREAD: "UNREAD",
  READ: "READ",
  ARCHIVED: "ARCHIVED",
} as const;

export type NotificationStatus =
  (typeof NotificationStatus)[keyof typeof NotificationStatus];

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  status: NotificationStatus;
  conversation_id?: string;
  task_id?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  read_at?: string;
}

export interface NotificationPage {
  items: Notification[];
  next_page_id?: string;
  total_count: number;
}

export interface NotificationSettings {
  email_enabled: boolean;
  slack_enabled: boolean;
  web_push_enabled: boolean;
  notification_types: Partial<Record<NotificationType, boolean>>;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  timezone: string;
}

export interface NotificationPreferences {
  user_id: string;
  settings: NotificationSettings;
  enabled: boolean;
  updated_at: string;
}

export interface CreateNotificationRequest {
  title: string;
  message: string;
  notification_type: NotificationType;
  priority?: NotificationPriority;
  conversation_id?: string;
  task_id?: string;
  metadata?: Record<string, unknown>;
}

export interface UpdateNotificationRequest {
  status?: NotificationStatus;
  metadata?: Record<string, unknown>;
}