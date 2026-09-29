import { AIShowcase } from "@/components/home/ai-showcase";
import { Categories } from "@/components/home/categories";
import { CTABanner } from "@/components/home/cta-banner";
import { FAQSection } from "@/components/home/faq-section";
import { FeaturedCompanies } from "@/components/home/featured-companies";
import { HeroSection } from "@/components/home/hero-section";
import { HowItWorks } from "@/components/home/how-it-works";
import { Newsletter } from "@/components/home/newsletter";
import { Testimonials } from "@/components/home/testimonials";
import { TrendingJobs } from "@/components/home/trending-jobs";

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <TrendingJobs />
      <FeaturedCompanies />
      <AIShowcase />
      <Categories />
      <HowItWorks />
      <Testimonials />
      <CTABanner />
      <FAQSection />
      <Newsletter />
    </>
  );
}
