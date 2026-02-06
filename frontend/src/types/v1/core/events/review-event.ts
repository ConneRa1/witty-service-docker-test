import { BaseEvent } from "../base/event";
import { SourceType } from "../base/common";

/**
 * Open review event
 * Fired when agent requests to open a preview for a web service
 */
export interface OpenReviewEvent extends BaseEvent {
  /**
   * The source is always "agent" for open review events
   */
  source: SourceType;

  /**
   * The event kind - supports both SDK (camelCase) and legacy (snake_case) formats
   */
  kind: "OpenReviewEvent" | "open_review_event";

  /**
   * Port where the service is running
   */
  port: number;

  /**
   * Human-readable service name
   */
  name: string;

  /**
   * Optional service description
   */
  description?: string;

  /**
   * Path prefix for the service (default: "/")
   */
  path: string;
}
