import type { Metadata } from "next";
import { LegalPage } from "@/components/shared/legal-page";
import { SITE } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The rules for using the JobsNexGen job portal as a candidate, employer or freelancer recruiter.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      updated="2 October 2026"
      intro={`These terms apply to everyone who uses www.jobsnexgen.com, run by ${SITE.name}. By creating an account or using the site you agree to them. If you don't agree, please don't use the site.`}
      sections={[
        {
          heading: "Your account",
          body: (
            <ul>
              <li>Give accurate information and keep it up to date.</li>
              <li>Keep your password private. You are responsible for what happens under your account; tell us straight away if you think someone else has used it.</li>
              <li>You must be 18 or older. One account per person.</li>
            </ul>
          ),
        },
        {
          heading: "Candidates",
          body: (
            <ul>
              <li>Your profile, resume and applications must be truthful and your own.</li>
              <li>When you apply for a job, you agree that we share your application and resume with that employer.</li>
              <li>Using the portal is free for candidates. {SITE.name} never asks candidates to pay for a job, an interview or an offer. If anyone asks you for money in our name, don&apos;t pay and report it to us.</li>
            </ul>
          ),
        },
        {
          heading: "Employers and freelance recruiters",
          body: (
            <ul>
              <li>Post only genuine, current vacancies that you are authorised to fill, with honest pay, location and requirements.</li>
              <li>Jobs posted by recruiters and freelancers are reviewed by our team and go live only after approval. We may reject, edit-request or remove any job that breaks these terms.</li>
              <li>Don&apos;t charge candidates any fee, and don&apos;t discriminate on grounds such as religion, caste, gender, disability or marital status.</li>
              <li>Use candidates&apos; data only to fill the job they applied for, and keep it confidential.</li>
              <li>Premium recruitment services for client companies are covered by a separate agreement (MOU) with {SITE.name}.</li>
            </ul>
          ),
        },
        {
          heading: "Things you must not do",
          body: (
            <ul>
              <li>Post false, misleading, offensive or illegal content.</li>
              <li>Collect other users&apos; data, send spam, or contact candidates for anything other than the job.</li>
              <li>Try to break into accounts or our systems, overload the site, or copy listings automatically.</li>
            </ul>
          ),
        },
        {
          heading: "Listings from other sites",
          body: <p>Some search results labelled &ldquo;live listings&rdquo; come from external job boards. We don&apos;t check or control those jobs; applying for them takes you to the other site and its own terms.</p>,
        },
        {
          heading: "No guarantee of a job",
          body: <p>We work to show genuine jobs and candidates, but we can&apos;t guarantee that an application leads to an interview or a job, or that every listing or profile is accurate. Employers make their own hiring decisions.</p>,
        },
        {
          heading: "Content and ownership",
          body: <p>You keep ownership of what you upload, and give us permission to store and display it to run the service. The site&apos;s design, software and brand belong to {SITE.name}.</p>,
        },
        {
          heading: "Limitation of liability",
          body: <p>The site is provided &ldquo;as is&rdquo;. As far as the law allows, {SITE.name} is not liable for indirect losses, or for the actions of employers, candidates or third-party sites. Nothing in these terms limits rights you have under Indian consumer law.</p>,
        },
        {
          heading: "Suspension and closing accounts",
          body: <p>We may suspend or close accounts that break these terms or put other users at risk. You can close your account at any time by contacting us.</p>,
        },
        {
          heading: "Law, changes and contact",
          body: <p>These terms are governed by the laws of India, and the courts of Bengaluru, Karnataka have jurisdiction. If we change them we will update the date at the top. Questions: {SITE.email} or {SITE.address}.</p>,
        },
      ]}
    />
  );
}
