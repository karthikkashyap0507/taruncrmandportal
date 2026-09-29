"""Run: python -m scripts.seed_jobs  (from backend directory with venv active)"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.models.recruiter import Recruiter
from app.auth.security import hash_password

COMPANIES = [
    {"name": "Google India", "website": "https://google.com", "industry": "Technology", "description": "Organising the world's information."},
    {"name": "Microsoft India", "website": "https://microsoft.com", "industry": "Technology", "description": "Empowering every person and organisation."},
    {"name": "Flipkart", "website": "https://flipkart.com", "industry": "E-Commerce", "description": "India's leading e-commerce platform."},
    {"name": "Zomato", "website": "https://zomato.com", "industry": "Food Tech", "description": "Delivering happiness, one meal at a time."},
    {"name": "CRED", "website": "https://cred.club", "industry": "FinTech", "description": "Reward good financial behaviour."},
    {"name": "Razorpay", "website": "https://razorpay.com", "industry": "FinTech", "description": "Full-stack payment solutions."},
    {"name": "Swiggy", "website": "https://swiggy.com", "industry": "Food Tech", "description": "Delivering food and groceries."},
    {"name": "PhonePe", "website": "https://phonepe.com", "industry": "FinTech", "description": "Payments app for everyone."},
]

JOBS = [
    {"title": "Senior Software Engineer - Backend", "company": "Google India", "salary_min": 3000000, "salary_max": 5000000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "4-7 years", "skills": ["Python", "Go", "Kubernetes", "GCP", "Distributed Systems"], "description": "Join our core infrastructure team building the next generation of Google's backend systems. You will design, develop, and deploy highly scalable services used by billions of users worldwide."},
    {"title": "Frontend Engineer - React", "company": "Google India", "salary_min": 2500000, "salary_max": 4000000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "3-5 years", "skills": ["React", "TypeScript", "GraphQL", "CSS", "Performance"], "description": "Build beautiful, performant UIs for Google's flagship products. Work with world-class designers and engineers to create experiences used by millions."},
    {"title": "ML Engineer - GenAI", "company": "Microsoft India", "salary_min": 3500000, "salary_max": 6000000, "location": "Hyderabad, Telangana", "employment_type": "full_time", "experience_level": "5-8 years", "skills": ["Python", "PyTorch", "LLMs", "Azure", "MLOps"], "description": "Work on cutting-edge Generative AI models integrated into Microsoft 365, Copilot, and Azure AI. Shape the future of AI-powered productivity tools."},
    {"title": "Data Engineer", "company": "Flipkart", "salary_min": 1800000, "salary_max": 3000000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-4 years", "skills": ["Apache Spark", "Python", "SQL", "Kafka", "Airflow"], "description": "Build and maintain robust data pipelines that power Flipkart's recommendations, analytics, and business intelligence systems."},
    {"title": "Product Manager - Growth", "company": "Zomato", "salary_min": 2000000, "salary_max": 3500000, "location": "Gurugram, Haryana", "employment_type": "full_time", "experience_level": "3-5 years", "skills": ["Product Strategy", "A/B Testing", "SQL", "Analytics", "User Research"], "description": "Drive growth initiatives for Zomato's marketplace. Work cross-functionally with engineering, design, and marketing to launch features that increase GMV and retention."},
    {"title": "Android Developer", "company": "CRED", "salary_min": 2000000, "salary_max": 3500000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "3-6 years", "skills": ["Kotlin", "Android SDK", "Jetpack Compose", "MVVM", "Coroutines"], "description": "Build CRED's award-winning Android app used by India's most creditworthy consumers. Focus on crafting delightful, pixel-perfect experiences."},
    {"title": "Full Stack Engineer", "company": "Razorpay", "salary_min": 1500000, "salary_max": 2800000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-4 years", "skills": ["Node.js", "React", "PostgreSQL", "AWS", "TypeScript"], "description": "Join Razorpay's payment products team. Build features that process billions in transactions for 8M+ merchants across India."},
    {"title": "DevOps Engineer", "company": "Swiggy", "salary_min": 1800000, "salary_max": 3200000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "3-5 years", "skills": ["Kubernetes", "Terraform", "AWS", "Docker", "CI/CD", "Helm"], "description": "Scale Swiggy's infrastructure to handle millions of daily orders. Work on reliability, observability, and deployment automation."},
    {"title": "UX Designer", "company": "PhonePe", "salary_min": 1200000, "salary_max": 2200000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-5 years", "skills": ["Figma", "User Research", "Prototyping", "Design Systems", "Accessibility"], "description": "Design intuitive payment experiences for 500M+ PhonePe users. Drive user research, create wireframes, and collaborate with product and engineering."},
    {"title": "iOS Developer", "company": "Flipkart", "salary_min": 2000000, "salary_max": 3500000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "3-5 years", "skills": ["Swift", "SwiftUI", "UIKit", "Xcode", "Core Data"], "description": "Develop Flipkart's iOS app, one of India's most-downloaded shopping apps. Work on performance, features, and exceptional UX for millions of customers."},
    {"title": "Security Engineer", "company": "Microsoft India", "salary_min": 3000000, "salary_max": 5500000, "location": "Hyderabad, Telangana", "employment_type": "full_time", "experience_level": "5-8 years", "skills": ["Penetration Testing", "SAST", "Cloud Security", "Zero Trust", "Python"], "description": "Protect Microsoft's cloud infrastructure and products from security threats. Conduct security reviews, threat modelling, and implement security best practices."},
    {"title": "SRE - Site Reliability Engineer", "company": "Google India", "salary_min": 3500000, "salary_max": 6000000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "4-7 years", "skills": ["Linux", "Python", "Go", "Monitoring", "Incident Response", "SLO"], "description": "Keep Google's production systems running at five nines. Own the reliability of services that power billions of searches, maps, and Gmail users."},
    {"title": "Backend Engineer - Node.js", "company": "CRED", "salary_min": 1800000, "salary_max": 3200000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-4 years", "skills": ["Node.js", "TypeScript", "MongoDB", "Redis", "Microservices"], "description": "Build CRED's backend services handling billions in credit card payments. Deliver high-performance APIs with clean architecture and great test coverage."},
    {"title": "Data Scientist - Recommendations", "company": "Swiggy", "salary_min": 2200000, "salary_max": 3800000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "3-5 years", "skills": ["Python", "ML", "Recommendation Systems", "Spark", "A/B Testing"], "description": "Power Swiggy's restaurant and dish recommendations using machine learning. Drive discovery and increase orders through personalised suggestions."},
    {"title": "Technical Program Manager", "company": "Razorpay", "salary_min": 2500000, "salary_max": 4500000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "5-8 years", "skills": ["Program Management", "Agile", "Risk Management", "Stakeholder Management", "SQL"], "description": "Drive complex technical programs across Razorpay's payment infrastructure. Coordinate between engineering, product, and business teams to deliver critical projects."},
    {"title": "React Native Developer", "company": "Zomato", "salary_min": 1500000, "salary_max": 2800000, "location": "Gurugram, Haryana", "employment_type": "full_time", "experience_level": "2-5 years", "skills": ["React Native", "JavaScript", "Redux", "Native Modules", "Performance"], "description": "Build Zomato's cross-platform mobile app used by 100M+ users to order food, groceries, and more. Optimize app performance and create delightful UX."},
    {"title": "Cloud Architect - AWS", "company": "Microsoft India", "salary_min": 4000000, "salary_max": 8000000, "location": "Remote", "employment_type": "full_time", "experience_level": "8-12 years", "skills": ["AWS", "Azure", "Architecture", "Cost Optimization", "Security", "IaC"], "description": "Design enterprise-grade cloud architectures for Microsoft's largest customers. Lead cloud migration and modernisation projects across industries."},
    {"title": "Software Engineer Intern", "company": "Flipkart", "salary_min": 60000, "salary_max": 80000, "location": "Bengaluru, Karnataka", "employment_type": "internship", "experience_level": "0-1 years", "skills": ["Python", "Java", "Data Structures", "Algorithms"], "description": "Join Flipkart's engineering team as an intern. Work on real features shipped to millions of users, guided by senior engineers. 6-month internship with PPO opportunity."},
    {"title": "QA Engineer - Automation", "company": "PhonePe", "salary_min": 1200000, "salary_max": 2000000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-4 years", "skills": ["Selenium", "Appium", "Python", "TestNG", "CI/CD"], "description": "Build and maintain PhonePe's test automation frameworks. Ensure quality of payment flows, UPI transactions, and financial features for 500M users."},
    {"title": "Blockchain Developer", "company": "CRED", "salary_min": 2500000, "salary_max": 4500000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "3-6 years", "skills": ["Solidity", "Web3.js", "Ethereum", "Smart Contracts", "DeFi"], "description": "Explore blockchain use cases for CRED's loyalty and rewards ecosystem. Build smart contracts and decentralised applications that add value for creditworthy Indians."},
    {"title": "AI/ML Research Scientist", "company": "Google India", "salary_min": 5000000, "salary_max": 10000000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "PhD or 6+ years", "skills": ["Deep Learning", "NLP", "Computer Vision", "PyTorch", "Research"], "description": "Conduct fundamental and applied research in AI/ML at Google Research India. Publish at top venues (NeurIPS, ICML, ACL) and transfer research into Google products."},
    {"title": "Technical Content Writer", "company": "Razorpay", "salary_min": 800000, "salary_max": 1400000, "location": "Remote", "employment_type": "full_time", "experience_level": "1-3 years", "skills": ["Technical Writing", "API Documentation", "Markdown", "Developer Experience"], "description": "Create world-class documentation, tutorials, and API guides for Razorpay's developer ecosystem. Help 8M+ developers integrate payments seamlessly."},
    {"title": "Business Analyst - Fintech", "company": "PhonePe", "salary_min": 1000000, "salary_max": 1800000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "1-3 years", "skills": ["SQL", "Excel", "Data Analysis", "Tableau", "Product Analytics"], "description": "Analyse PhonePe's transaction data to uncover growth opportunities. Work with product and engineering teams to define metrics, build dashboards, and drive decisions."},
    {"title": "Growth Hacker / Marketing Tech", "company": "Swiggy", "salary_min": 1200000, "salary_max": 2200000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-4 years", "skills": ["Marketing Automation", "SEO", "Analytics", "Python", "CRM"], "description": "Drive user acquisition and retention for Swiggy through data-driven marketing experiments. Own the marketing tech stack and run campaigns that reach 50M+ users."},
    {"title": "Cybersecurity Analyst", "company": "Flipkart", "salary_min": 1500000, "salary_max": 2500000, "location": "Bengaluru, Karnataka", "employment_type": "full_time", "experience_level": "2-5 years", "skills": ["SOC", "SIEM", "Threat Intelligence", "Incident Response", "VAPT"], "description": "Monitor and protect Flipkart's e-commerce platform from cyber threats. Work in the SOC team, analyse threats, and implement security controls for India's largest retailer."},
]


def seed():
    db = SessionLocal()
    try:
        # Create a system recruiter user if not exists
        system_user = db.query(User).filter(User.email == "recruiter@jobsnexgen.in").first()
        if not system_user:
            system_user = User(
                name="JobsNexGen Recruiter",
                email="recruiter@jobsnexgen.in",
                password_hash=hash_password("Recruiter@123!"),
                role=UserRole.recruiter,
            )
            db.add(system_user)
            db.flush()

        # Create companies
        company_map = {}
        for c_data in COMPANIES:
            company = db.query(Company).filter(Company.name == c_data["name"]).first()
            if not company:
                company = Company(**c_data)
                db.add(company)
                db.flush()
            company_map[c_data["name"]] = company

        # Create recruiter profile linked to first company
        first_company = list(company_map.values())[0]
        recruiter = db.query(Recruiter).filter(Recruiter.user_id == system_user.id).first()
        if not recruiter:
            recruiter = Recruiter(user_id=system_user.id, company_id=first_company.id)
            db.add(recruiter)
            db.flush()

        # Create jobs
        existing_titles = {j.title for j in db.query(Job.title).all()}
        created = 0
        for j_data in JOBS:
            if j_data["title"] in existing_titles:
                continue
            company = company_map.get(j_data["company"])
            if not company:
                continue
            # Temporarily set recruiter's company for each job
            job = Job(
                title=j_data["title"],
                description=j_data["description"],
                company_id=company.id,
                recruiter_id=recruiter.id,
                salary_min=j_data["salary_min"],
                salary_max=j_data["salary_max"],
                location=j_data["location"],
                employment_type=j_data["employment_type"],
                experience_level=j_data["experience_level"],
                skills=j_data["skills"],
                status=JobStatus.published,
            )
            db.add(job)
            created += 1

        db.commit()
        print(f"[OK] Seeded {len(company_map)} companies and {created} new jobs successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
