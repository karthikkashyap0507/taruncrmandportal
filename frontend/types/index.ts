export type UserRole = "candidate" | "recruiter" | "company_admin" | "platform_admin";
export type JobStatus = "draft" | "pending" | "published" | "rejected" | "closed";
export type EducationLevel = "any" | "10th" | "12th" | "iti" | "diploma" | "graduate" | "postgraduate";
export type SalaryPeriod = "month" | "year";
export type ApplicationStatus = "applied" | "screening" | "interview" | "offered" | "hired" | "rejected" | "withdrawn";
export type EmploymentType = "full_time" | "part_time" | "contract" | "internship" | "remote";

export interface ExperienceItem {
  company: string;
  role: string;
  startDate: string;
  endDate: string;
  description: string;
}

export interface Candidate {
  id: number;
  user_id: number;
  headline?: string;
  skills: string[];
  experience: ExperienceItem[];
  resume_url?: string;
  profile_score: number;
}

export interface CandidateUpdate {
  headline?: string;
  skills?: string[];
  experience?: ExperienceItem[];
  resume_url?: string;
}

export interface Recruiter {
  id: number;
  user_id: number;
  company_id: number;
}

export interface Company {
  id: number;
  name: string;
  logo?: string;
  website?: string;
  description?: string;
  industry?: string;
  openPositions?: number;
}

export interface Job {
  id: number;
  company_id: number;
  recruiter_id: number;
  title: string;
  description: string;
  salary_min?: number;
  salary_max?: number;
  skills: string[];
  experience_level?: string;
  location?: string;
  locality?: string;
  education?: EducationLevel;
  salary_period?: SalaryPeriod;
  employment_type?: string;
  status: JobStatus;
  review_note?: string | null;
  is_premium?: boolean;
  source?: "portal" | "crm";
  expires_at?: string | null;
  created_at?: string;
  updated_at?: string;
  company?: Company;
}

export interface JobCreate {
  title: string;
  description: string;
  salary_min?: number;
  salary_max?: number;
  skills?: string[];
  experience_level?: string;
  location?: string;
  locality?: string;
  education?: EducationLevel;
  salary_period?: SalaryPeriod;
  employment_type?: string;
  status?: JobStatus;
}

export interface JobUpdate {
  title?: string;
  description?: string;
  salary_min?: number;
  salary_max?: number;
  skills?: string[];
  experience_level?: string;
  location?: string;
  locality?: string;
  education?: EducationLevel;
  salary_period?: SalaryPeriod;
  employment_type?: string;
  status?: JobStatus;
}

export interface CandidateInfo {
  user_id: number;
  name: string;
  email: string;
  headline?: string;
  skills: string[];
  resume_url?: string;
}

export interface Application {
  id: number;
  candidate_id: number;
  job_id: number;
  status: ApplicationStatus;
  score?: number;
  applied_at: string;
  full_name?: string;
  phone?: string;
  years_experience?: number;
  cover_letter?: string;
  resume_url?: string;
  education?: EducationLevel | null;
  expected_salary?: number | null;
  current_location?: string | null;
  candidate_info?: CandidateInfo;
  job?: Job;
}

export interface ApplicationCreate {
  full_name?: string;
  phone?: string;
  years_experience?: number;
  cover_letter?: string;
  resume_url?: string;
  education?: EducationLevel;
  expected_salary?: number;
  current_location?: string;
}

export interface ApplicationUpdate {
  status?: ApplicationStatus;
  score?: number;
}

export type MessageType = "message" | "approval" | "rejection" | "interview_invite" | "offer";

export interface AppMessage {
  id: number;
  application_id: number;
  job_id?: number;
  job_title?: string;
  sender_id: number;
  sender_name: string;
  message_type: MessageType;
  content: string;
  created_at: string;
  status?: ApplicationStatus;
}

export interface SavedJob {
  id: number;
  job_id: number;
  saved_at: string;
  job: Job;
}

export interface ExternalJob {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  salary_min?: number;
  salary_max?: number;
  employment_type?: string;
  redirect_url: string;
  source: string;
}

export interface Testimonial {
  id: number;
  name: string;
  role: string;
  company: string;
  avatar?: string;
  quote: string;
  rating: number;
}

export interface Service {
  id: number;
  title: string;
  description: string;
  price: string;
  features: string[];
  popular?: boolean;
}

export interface Stat {
  label: string;
  value: number;
  suffix?: string;
}

export interface ATSResult {
  application_id: number;
  total: number;
  skills_score: number;
  exp_score: number;
  kw_score: number;
  matched_skills: string[];
  total_job_skills: number;
  matched_keywords: number;
  total_keywords: number;
  candidate_years: number;
  required_exp: string;
}
