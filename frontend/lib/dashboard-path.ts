import type { UserRole } from "@/types";

export function dashboardPathForRole(role: UserRole): string {
  switch (role) {
    case "candidate":
      return "/dashboard/candidate";
    case "recruiter":
      return "/dashboard/recruiter";
    case "company_admin":
      return "/dashboard/company";
    case "platform_admin":
      return "/dashboard/admin";
    default:
      return "/";
  }
}
