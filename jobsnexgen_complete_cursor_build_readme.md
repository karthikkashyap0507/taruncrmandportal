# JobsNexGen — Complete Production-Level AI Job Portal

# Project Overview

## Project Name
JobsNexGen

## Tagline
Next Generation AI-Powered Hiring Platform

## Vision
Build a world-class AI-powered job portal platform similar to:
- entity["company","LinkedIn","Professional networking and jobs platform"]
- entity["company","Indeed","Global job search platform"]
- entity["company","Naukri.com","Indian job portal platform"]
- entity["company","Glassdoor","Jobs and employer review platform"]

The platform must be:
- Production-ready
- Mobile-first
- AI-powered
- Modern UI/UX
- Highly scalable
- Enterprise-grade
- SEO optimized
- Real-time enabled
- Fully responsive
- Interactive and animated

---

# PRIMARY OBJECTIVE FOR CURSOR

Cursor must generate:
- Production-level code
- Clean architecture
- Modular reusable components
- Mobile-first responsive UI
- Smooth animations
- Enterprise-grade backend
- Optimized database queries
- Secure authentication
- AI integrations
- Real-time systems
- Beautiful dashboards
- Advanced search system
- ATS system
- Resume parsing
- Admin management
- Subscription system
- Scalable deployment-ready infrastructure

---

# UI/UX DESIGN REQUIREMENTS

# IMPORTANT DESIGN GOAL
The UI must look more modern and attractive than:
- entity["company","LinkedIn","Professional networking and jobs platform"]
- entity["company","Indeed","Global job search platform"]
- entity["company","Naukri.com","Indian job portal platform"]

The design should feel like:
- Modern SaaS platform
- AI startup product
- Premium startup ecosystem
- Futuristic and minimal
- Fast and interactive

---

# DESIGN SYSTEM

## Brand Colors
Primary: #3B82F6
Secondary: #8B5CF6
Accent: #06B6D4
Success: #10B981
Danger: #EF4444
Background: #0F172A
Card Background: #111827
Text Primary: #FFFFFF
Text Secondary: #94A3B8

---

# Typography
Use:
- Inter
- Poppins
- Satoshi

Headings:
- Bold
- Large
- Modern

Body:
- Clean
- Highly readable

---

# UI STYLE

Use:
- Glassmorphism
- Soft gradients
- Smooth shadows
- Rounded corners
- Subtle animations
- Motion effects
- Hover interactions
- Floating cards
- Dynamic backgrounds

---

# ANIMATIONS

Use:
- Framer Motion
- Smooth page transitions
- Skeleton loaders
- Animated counters
- Interactive hover effects
- Floating hero elements
- Gradient animations
- Scroll animations
- Micro-interactions

---

# MOBILE-FIRST REQUIREMENTS

VERY IMPORTANT:
The entire application must be:
- Fully responsive
- Touch optimized
- Fast on mobile
- PWA ready
- App-like experience

Mobile requirements:
- Bottom navigation
- Swipe interactions
- Mobile side drawer
- Optimized cards
- Responsive typography
- Responsive dashboards
- Fast loading
- Lazy loading

---

# TECH STACK

# Frontend

Use:
- Next.js 15
- TypeScript
- Tailwind CSS
- ShadCN UI
- Framer Motion
- Zustand
- React Query
- Axios
- React Hook Form
- Zod validation

---

# Backend

Use:
- FastAPI
- Python
- SQLAlchemy
- Pydantic
- Alembic
- JWT Authentication
- OAuth2

---

# Database

Primary Database:
- PostgreSQL

Additional Services:
- Redis
- Elasticsearch
- Qdrant

---

# AI STACK

Use:
- OpenAI API
- LangChain
- Sentence Transformers
- spaCy
- OCR support
- Resume parsing pipeline

---

# FILE STORAGE

Use:
- AWS S3
OR
- Cloudinary

---

# AUTHENTICATION

Implement:
- JWT auth
- Google login
- GitHub login
- LinkedIn login
- Refresh tokens
- Role-based access

Roles:
- Candidate
- Recruiter
- Company Admin
- Platform Admin

---

# DEVOPS

Use:
- Docker
- Docker Compose
- GitHub Actions
- NGINX
- Kubernetes-ready setup

---

# PROJECT STRUCTURE

# Frontend Structure

```bash
frontend/
 ├── app/
 ├── components/
 │   ├── ui/
 │   ├── shared/
 │   ├── dashboard/
 │   ├── jobs/
 │   ├── auth/
 │   ├── recruiter/
 │   └── candidate/
 ├── hooks/
 ├── services/
 ├── store/
 ├── lib/
 ├── utils/
 ├── types/
 ├── styles/
 └── public/
```

---

# Backend Structure

```bash
backend/
 ├── app/
 │   ├── api/
 │   ├── models/
 │   ├── schemas/
 │   ├── services/
 │   ├── repositories/
 │   ├── middleware/
 │   ├── ai/
 │   ├── auth/
 │   ├── utils/
 │   ├── core/
 │   └── workers/
 ├── tests/
 ├── docker/
 └── scripts/
```

---

# CORE FEATURES

# 1. Candidate Features

Implement:
- Registration/Login
- Social authentication
- Profile management
- Resume upload
- Resume builder
- AI resume optimization
- Skill tagging
- Experience management
- Education management
- Certifications
- Portfolio links
- GitHub integration
- LinkedIn integration
- AI profile scoring
- Saved jobs
- Job applications
- Application tracking
- Job alerts
- AI recommendations
- AI-generated cover letters
- Video introduction
- Skill assessments
- Mock interviews
- Real-time notifications
- Interview scheduling
- Salary insights
- Career roadmap

---

# 2. Recruiter Features

Implement:
- Recruiter onboarding
- Company verification
- Company dashboard
- Post jobs
- Manage jobs
- ATS system
- Candidate filtering
- AI candidate ranking
- Interview scheduling
- Bulk hiring
- Talent pipeline
- Resume database access
- Advanced analytics
- Team collaboration
- Subscription plans
- Payment system
- Candidate notes
- AI-generated job descriptions
- Automated email workflows

---

# 3. Admin Features

Implement:
- Admin dashboard
- User management
- Recruiter verification
- Job moderation
- Fraud detection
- AI moderation
- Reports handling
- Subscription management
- Revenue analytics
- System analytics
- Platform settings
- CMS management
- Activity logs

---

# 4. AI FEATURES

Implement advanced AI systems:

## Resume Parsing
Extract:
- Skills
- Experience
- Education
- Certifications
- Keywords
- ATS score

---

## AI Job Matching
Use embeddings for:
- Semantic matching
- Personalized recommendations
- Smart ranking

---

## AI Career Coach
Provide:
- Resume feedback
- Interview tips
- Skill suggestions
- Career growth roadmap

---

## AI Interview System
Implement:
- AI interviewer
- Voice-based interview
- Technical assessments
- Communication scoring

---

# SEARCH SYSTEM

Use Elasticsearch.

Implement:
- Full-text search
- Typo tolerance
- Filters
- Semantic search
- Suggestions
- Trending searches
- Personalized ranking
- Fast search indexing

Filters:
- Skills
- Location
- Salary
- Experience
- Remote jobs
- Job type
- Industry
- Company

---

# REAL-TIME FEATURES

Use WebSockets.

Implement:
- Live notifications
- Live chat
- Real-time updates
- Interview alerts
- Application tracking

---

# PAYMENT SYSTEM

Integrate:
- Razorpay
- Stripe

Subscription Plans:
- Free
- Pro
- Premium
- Enterprise

Features:
- Featured jobs
- Priority applicants
- AI hiring tools
- Resume database access

---

# DATABASE DESIGN

# Main Tables

## Users
- id
- name
- email
- password_hash
- role
- created_at

---

## Candidates
- id
- user_id
- headline
- skills
- experience
- resume_url
- profile_score

---

## Companies
- id
- name
- logo
- website
- description
- industry

---

## Recruiters
- id
- user_id
- company_id

---

## Jobs
- id
- company_id
- recruiter_id
- title
- description
- salary
- skills
- experience_level
- location
- employment_type
- status

---

## Applications
- id
- candidate_id
- job_id
- status
- score
- applied_at

---

## Interviews
- id
- application_id
- interview_type
- scheduled_at
- feedback

---

## Notifications
- id
- user_id
- type
- message
- read_status

---

# MAIN WEBSITE NAVIGATION

The main navbar must contain these pages exactly:

1. Home
2. Jobs
3. About Us
4. Add On Services
5. Contact Us
6. Sign In

---

# PAGE-WISE REQUIREMENTS

# 1. HOME PAGE

The Home page must be ultra-modern, highly interactive, mobile-first, and visually stunning.

Sections:
- Premium animated hero section
- AI-powered search bar
- Trending jobs section
- Featured companies
- AI hiring showcase
- Platform statistics
- Testimonials carousel
- Top categories
- Why choose JobsNexGen
- How it works
- Premium CTA banners
- Pricing preview
- FAQ section
- Newsletter subscription
- Footer

Hero Section Requirements:
- Massive modern heading
- Animated gradient text
- Floating cards
- Motion backgrounds
- AI search animation
- Interactive search bar
- CTA buttons
- Animated counters
- Futuristic visuals

Animations:
- Framer Motion animations
- Scroll reveal effects
- Floating glass cards
- Hover interactions
- Dynamic gradients
- Smooth transitions

---

# 2. JOBS PAGE

The Jobs page should feel better than modern job portals.

Features:
- Advanced search bar
- AI-powered recommendations
- Smart filters
- Location filters
- Salary filters
- Experience filters
- Remote jobs filter
- Job cards
- Save jobs
- Quick apply
- One-click AI apply
- Pagination
- Infinite scrolling
- Skeleton loading
- Responsive design

Job Card Design:
- Glassmorphism cards
- Company logo
- Salary range
- Experience level
- Skills tags
- Remote badge
- Apply button
- Save button
- Hover animations

---

# 3. ABOUT US PAGE

The About Us page should tell a premium startup story.

Sections:
- Company introduction
- Mission and vision
- AI innovation story
- Why JobsNexGen
- Team section
- Timeline section
- Platform achievements
- Statistics
- Testimonials
- CTA section

Design:
- Premium storytelling UI
- Scroll animations
- Interactive timeline
- Animated statistics
- Modern gradients
- Responsive layouts

---

# 4. ADD ON SERVICES PAGE

This page should showcase premium hiring and career services.

Services:
- AI Resume Building
- Resume Optimization
- LinkedIn Profile Optimization
- AI Career Coaching
- Mock Interviews
- Premium Job Boosting
- AI ATS Resume Scoring
- Skill Assessments
- Recruitment Services
- Featured Employer Branding

UI Requirements:
- Premium pricing cards
- Interactive comparisons
- Animated service cards
- Glassmorphism effects
- Hover effects
- CTA sections

---

# 5. CONTACT US PAGE

Features:
- Contact form
- Company email
- Phone number
- Office location
- Google Maps integration
- Social media links
- FAQ section
- Live chat widget

Design:
- Split layout
- Interactive form
- Animated backgrounds
- Responsive contact cards
- Smooth transitions

---

# 6. SIGN IN PAGE

Features:
- Login
- Register
- Google authentication
- GitHub authentication
- LinkedIn authentication
- Forgot password
- OTP verification
- Role selection

UI Requirements:
- Futuristic authentication UI
- Glassmorphism login card
- Animated backgrounds
- Smooth form transitions
- Mobile-first layout
- AI-inspired visual design

---

# LANDING PAGE REQUIREMENTS

Create an ultra-modern landing page.

Sections:
- Hero section
- Animated background
- AI job search
- Trending jobs
- Featured companies
- Testimonials
- Platform stats
- AI features showcase
- Success stories
- Pricing plans
- FAQ section
- Footer

Hero Section Requirements:
- Large animated heading
- Search bar
- Floating UI cards
- Motion effects
- Gradient backgrounds
- CTA buttons
- AI-powered search showcase

---

# DASHBOARD REQUIREMENTS

# Candidate Dashboard

Include:
- Profile completion
- Recommended jobs
- Recent applications
- Saved jobs
- AI insights
- Notifications
- Interview schedules
- Resume score
- Skill analytics

---

# Recruiter Dashboard

Include:
- Hiring analytics
- Active jobs
- Candidate pipeline
- AI recommendations
- Team collaboration
- Revenue analytics
- Job performance charts

---

# ADMIN DASHBOARD

Include:
- Platform stats
- Revenue charts
- User growth
- Fraud alerts
- Recruiter approvals
- Reports management
- AI moderation insights

---

# API REQUIREMENTS

Implement REST APIs.

Endpoints:

## Auth APIs
- login
- register
- refresh token
- forgot password
- reset password

---

## Job APIs
- create job
- update job
- delete job
- get jobs
- apply job
- save job

---

## Candidate APIs
- update profile
- upload resume
- get recommendations

---

## Recruiter APIs
- candidate pipeline
- analytics
- ATS management

---

# SECURITY REQUIREMENTS

MANDATORY:
- HTTPS
- JWT security
- RBAC
- Rate limiting
- SQL injection prevention
- XSS protection
- CSRF protection
- File upload validation
- Secure password hashing
- Audit logs
- API throttling

---

# PERFORMANCE REQUIREMENTS

Optimize for:
- Lighthouse score above 95
- Fast loading
- SEO optimization
- Image optimization
- Lazy loading
- Code splitting
- Server-side rendering
- CDN usage
- Redis caching

---

# SEO REQUIREMENTS

Implement:
- Dynamic metadata
- Open Graph
- Structured data
- Sitemap
- robots.txt
- Canonical URLs
- SEO-friendly routes

---

# ACCESSIBILITY REQUIREMENTS

Implement:
- ARIA labels
- Keyboard navigation
- Screen reader support
- Proper contrast ratios
- Responsive typography

---

# TESTING REQUIREMENTS

Implement:
- Unit tests
- Integration tests
- API tests
- End-to-end tests

Use:
- Jest
- Playwright
- Pytest

---

# DEPLOYMENT REQUIREMENTS

Frontend:
- Vercel
OR
- AWS Amplify

Backend:
- AWS EC2
- Docker containers
- NGINX reverse proxy

Database:
- AWS RDS PostgreSQL

Storage:
- AWS S3

---

# CI/CD REQUIREMENTS

Implement GitHub Actions:
- Linting
- Testing
- Build
- Deployment
- Docker image creation

---

# MONITORING

Use:
- Grafana
- Prometheus
- Sentry
- ELK Stack

---

# EXTRA PREMIUM FEATURES

Implement:
- AI voice assistant
- AI career roadmap
- AI resume enhancement
- One-click AI apply
- WhatsApp job alerts
- Voice search
- AI mock interviews
- AI salary prediction
- Skill gap analysis
- Gamification
- Leaderboards
- Referral system
- Internal messaging
- Video resumes
- Coding assessments

---

# CODING STANDARDS FOR CURSOR

VERY IMPORTANT:

Cursor must:
- Write scalable code
- Use reusable components
- Use proper naming conventions
- Use clean architecture
- Follow SOLID principles
- Use TypeScript strictly
- Write modular backend services
- Add comments where necessary
- Optimize API calls
- Use environment variables
- Use reusable hooks
- Use reusable utility functions
- Implement proper error handling
- Use loading states
- Use skeleton loaders
- Use optimistic UI updates

---

# UI COMPONENT REQUIREMENTS

Create reusable components:
- Navbar
- Sidebar
- Mobile navigation
- Job cards
- Candidate cards
- Dashboard cards
- Analytics charts
- Search bars
- Filters
- Modals
- Drawers
- Tables
- Tabs
- AI chat widget
- Notification system

---

# IMPORTANT MOBILE UI INSTRUCTIONS

Cursor must ensure:
- Perfect responsiveness
- No overflow issues
- Mobile-friendly tables
- Responsive charts
- Optimized spacing
- Touch-friendly buttons
- Fast mobile performance
- Bottom mobile navigation
- Sticky mobile actions

---

# REQUIRED USER EXPERIENCE

The app should feel:
- Fast
- Premium
- Futuristic
- Interactive
- Smooth
- Professional
- AI-first
- Enterprise-grade

Every page must:
- Have animations
- Use loading states
- Use smooth transitions
- Be visually attractive
- Feel modern

---

# FINAL BUILD GOAL

Cursor must build:
- Full-stack production-ready platform
- Complete responsive UI
- AI-powered job ecosystem
- Enterprise-grade architecture
- Fully scalable infrastructure
- Highly polished UX/UI
- Real-world deployable application

The final product should be capable of scaling to millions of users and competing with:
- entity["company","LinkedIn","Professional networking and jobs platform"]
- entity["company","Indeed","Global job search platform"]
- entity["company","Naukri.com","Indian job portal platform"]

---

# FINAL INSTRUCTION TO CURSOR

Build JobsNexGen as a world-class modern AI-powered hiring platform with:
- Stunning UI
- Mobile-first experience
- Advanced AI capabilities
- Real-time systems
- Production-ready architecture
- Enterprise scalability
- Secure infrastructure
- Beautiful dashboards
- Smooth interactions
- Premium animations
- Best-in-class user experience

Every feature should feel polished, futuristic, and production-ready.

