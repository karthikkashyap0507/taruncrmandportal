"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  Award,
  Building2,
  Cpu,
  Globe,
  Search,
  Smartphone,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { SectionHeading } from "@/components/shared/section-heading";
import { CTABanner } from "@/components/home/cta-banner";
import { Button } from "@/components/ui/button";
import {
  DIGITAL_SERVICES,
  PROFESSIONAL_SERVICES,
  SERVICES_WHY_CHOOSE,
} from "@/lib/site-content";

const digitalIcons = [Search, Globe, Zap, Cpu, Smartphone];
const professionalIcons = [Building2, Wrench, Users, Award, Cpu, Globe];
const whyIcons = [Award, Users, Globe];

export default function ServicesPage() {
  return (
    <div className="pb-24">
      <section className="hero-glow py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Add On Services"
            title="JobsNexgen Services"
            description="Digital solutions and professional services to grow your business and support your workforce."
          />
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            align="left"
            title="Digital Services"
            description="Transform your online presence and operations with our expert digital solutions."
            className="mb-10"
          />
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {DIGITAL_SERVICES.map((service, i) => {
              const Icon = digitalIcons[i] ?? Search;
              return (
                <motion.div
                  key={service.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                  whileHover={{ y: -6 }}
                  className="glass-card flex flex-col p-6"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#3B82F6]/20">
                    <Icon className="h-6 w-6 text-[#3B82F6]" />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{service.title}</h3>
                  <p className="mt-3 flex-1 text-sm leading-relaxed text-[#94A3B8]">
                    {service.description}
                  </p>
                  <Link href="/contact" className="mt-6">
                    <Button className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                      {service.cta}
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-[#111827]/50 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            align="left"
            title="Professional Services"
            description="Comprehensive on-ground and business support services for corporates and homes."
            className="mb-10"
          />
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {PROFESSIONAL_SERVICES.map((service, i) => {
              const Icon = professionalIcons[i] ?? Wrench;
              return (
                <motion.div
                  key={service.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                  whileHover={{ y: -6 }}
                  className="glass-card flex flex-col p-6"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#8B5CF6]/20">
                    <Icon className="h-6 w-6 text-[#8B5CF6]" />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{service.title}</h3>
                  <p className="mt-3 flex-1 text-sm leading-relaxed text-[#94A3B8]">
                    {service.description}
                  </p>
                  <div className="mt-6 flex gap-2">
                    <Link href="/contact" className="flex-1">
                      <Button variant="outline" className="w-full border-white/10 bg-white/5">
                        Learn More
                      </Button>
                    </Link>
                    <Link href="/contact" className="flex-1">
                      <Button className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                        Interested
                      </Button>
                    </Link>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            title={SERVICES_WHY_CHOOSE.title}
            description={SERVICES_WHY_CHOOSE.subtitle}
          />
          <div className="grid gap-6 md:grid-cols-3">
            {SERVICES_WHY_CHOOSE.items.map((item, i) => {
              const Icon = whyIcons[i] ?? Award;
              return (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="glass-card p-6 text-center"
                >
                  <Icon className="mx-auto mb-4 h-10 w-10 text-[#06B6D4]" />
                  <h3 className="font-semibold text-white">{item.title}</h3>
                  <p className="mt-2 text-sm text-[#94A3B8]">{item.description}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <CTABanner />
    </div>
  );
}
