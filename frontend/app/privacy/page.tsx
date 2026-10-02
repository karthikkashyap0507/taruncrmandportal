import type { Metadata } from "next";
import { LegalPage } from "@/components/shared/legal-page";
import { SITE } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How JobsNexGen collects, uses, shares and protects your personal data.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      updated="2 October 2026"
      intro={`This policy explains what personal data ${SITE.name} collects when you use www.jobsnexgen.com, why we collect it, who can see it and the choices you have. It is written to meet India's Digital Personal Data Protection Act, 2023 and the Information Technology Act, 2000.`}
      sections={[
        {
          heading: "Who we are",
          body: <p>{SITE.name} runs this job portal and a recruitment service for client companies. Address: {SITE.address}. You can reach us at {SITE.email} or through the contact page.</p>,
        },
        {
          heading: "What we collect",
          body: (
            <ul>
              <li><strong>Account details:</strong> name, email address, phone number and your password (stored only as a one-way hash, never in readable form).</li>
              <li><strong>Candidate profile:</strong> headline, skills, work experience and the resume you upload.</li>
              <li><strong>Job applications:</strong> the details you give when applying, such as phone number, years of experience, highest qualification, expected monthly salary, current location and any message to the employer.</li>
              <li><strong>Employer and freelancer details:</strong> company name and the jobs you post.</li>
              <li><strong>Contact form and job alerts:</strong> the name, email and message you send us, and your email if you sign up for weekly job alerts.</li>
              <li><strong>Security information:</strong> IP address, signed-in devices and sign-in attempts, used to protect accounts (for example, locking an account after repeated wrong passwords).</li>
            </ul>
          ),
        },
        {
          heading: "How we use it",
          body: (
            <ul>
              <li>To run your account, show you jobs and let you apply.</li>
              <li>To pass your application to the employer you applied to, and to score how well your profile matches the job.</li>
              <li>To send emails you need: welcome and password emails, application status updates, interview and joining reminders, and weekly job alerts if you asked for them.</li>
              <li>To keep the service secure and prevent fraud and misuse.</li>
              <li>To meet our legal obligations.</li>
            </ul>
          ),
        },
        {
          heading: "Who can see your data",
          body: (
            <>
              <ul>
                <li><strong>Employers:</strong> when you apply, the employer for that job sees your application and resume. Resumes are opened through private links that expire after 30 minutes, so they can&apos;t be shared onwards from our site.</li>
                <li><strong>Our recruitment team:</strong> for jobs we handle for paying clients, our staff see applicants in our internal recruitment system so they can schedule interviews and follow up.</li>
                <li><strong>Service providers:</strong> our servers are hosted by Google Cloud in India, and emails are sent through our email provider. They process data only on our instructions.</li>
                <li><strong>Authorities:</strong> when the law requires it.</li>
              </ul>
              <p>We do not sell your personal data, and we do not use advertising trackers.</p>
            </>
          ),
        },
        {
          heading: "Cookies and similar storage",
          body: <p>We keep you signed in using your browser&apos;s storage. We do not use advertising or cross-site tracking cookies. Clearing your browser data signs you out.</p>,
        },
        {
          heading: "How we protect it",
          body: <p>The site uses encrypted HTTPS connections. Passwords are hashed, resumes are stored privately, and access inside our systems depends on each person&apos;s role. Our servers&apos; disks, including the nightly backups we keep for 14 days, are encrypted by Google Cloud.</p>,
        },
        {
          heading: "How long we keep it",
          body: <p>We keep your data while your account is active. If you ask us to delete your account, we delete your profile and resume, and copies in backups disappear within 14 days. We may keep limited records of placements and invoices for as long as tax and accounting laws require.</p>,
        },
        {
          heading: "Your rights",
          body: (
            <ul>
              <li>See the personal data we hold about you, and correct it (most of it you can edit yourself in your profile).</li>
              <li>Ask us to delete your account and data, or withdraw consent you gave earlier.</li>
              <li>Unsubscribe from job alerts at any time with the link in every alert email.</li>
              <li>Raise a grievance with us, and if you are not satisfied, with the Data Protection Board of India.</li>
            </ul>
          ),
        },
        {
          heading: "Children",
          body: <p>The portal is meant for people aged 18 and over. We do not knowingly collect data from children.</p>,
        },
        {
          heading: "Changes and contact",
          body: <p>If we change this policy we will update the date at the top. For questions, requests or grievances, write to {SITE.email} or to {SITE.address}. We aim to reply within 7 working days.</p>,
        },
      ]}
    />
  );
}
