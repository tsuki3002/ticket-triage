export type TicketStatus =
  | "Open"
  | "Assigned"
  | "In Progress"
  | "Waiting for Customer"
  | "Resolved"
  | "Closed";

export interface Ticket {
  id: number;
  customer_name: string;
  customer_email: string;
  subject: string;
  description: string;
  product_module: string | null;
  attachment_link: string | null;

  summary: string | null;
  category: string | null;
  priority: string | null;
  priority_reason: string | null;
  recommended_team: string | null;
  suggested_response: string | null;

  assigned_team_id: number | null;
  assigned_user_id: number | null;
  status: TicketStatus;

  created_at: string;
  updated_at: string;
}

export interface Comment {
  id: number;
  ticket_id: number;
  author_id: number;
  text: string;
  created_at: string;
}

export interface Activity {
  id: number;
  ticket_id: number;
  user_id: number | null;
  activity_type: string;
  description: string;
  timestamp: string;
}