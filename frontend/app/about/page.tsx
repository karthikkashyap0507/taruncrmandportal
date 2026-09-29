"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  Globe,
  Handshake,
  Lightbulb,
  Shield,
  UserPlus,
  Users,
} from "lucide-react";
import { SectionHeading } from "@/components/shared/section-heading";
import { ImpactStat } from "@/components/shared/impact-stat";
import { CTABanner } from "@/components/home/cta-banner";
import { ABOUT_CONTENT } from "@/lib/site-content";

const stepIcons = [UserPlus, Users, CheckCircle2];

export default function AboutPage() {
  const { hero, intro, whyChoose, howItWorks, impact, partnership } = ABOUT_CONTENT;

  return (
    <div className="pb-24">
      <section className="hero-glow py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="About Us"
            title={hero.title}
            description={hero.subtitle}
          />
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="space-y-5 text-[#94A3B8] leading-relaxed"
          >
            {intro.map((paragraph) => (
              <p key={paragraph.slice(0, 40)}>{paragraph}</p>
            ))}
          </motion.div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-[#111827]/50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading title="Why Choose JobsNexgen?" />
          <ul className="mx-auto grid max-w-3xl gap-4 sm:grid-cols-2">
            {whyChoose.map((item, i) => (
              <motion.li
                key={item}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4"
              >
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[#10B981]" />
                <span className="text-sm text-white sm:text-base">{item}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      </section>

      <section className="py-20">
        <motion.div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            title={howItWorks.title}
            description={howItWorks.subtitle}
          />
          <div className="grid gap-8 md:grid-cols-3">
            {howItWorks.steps.map((step, i) => {
              const Icon = stepIcons[i] ?? UserPlus;
              return (
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  whileHover={{ y: -4 }}
                  className="glass-card relative p-6 text-center"
                >
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6]">
                    <Icon className="h-7 w-7 text-white" />
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#3B82F6]">
                    Step {i + 1}
                  </span>
                  <h3 className="mt-2 font-heading text-xl font-bold text-white">
                    {step.title}
                  </h3>
                  <p className="mt-3 text-sm text-[#94A3B8]">{step.description}</p>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </section>

      <section className="border-y border-white/10 bg-[#111827]/30 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading title="Our Impact" />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {impact.map((stat, i) => (
              <ImpactStat
                key={stat.label}
                value={stat.value}
                suffix={stat.suffix}
                label={stat.label}
                isDecimal={"isDecimal" in stat && stat.isDecimal}
                index={i}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow={partnership.title}
            title={`Partnership with ${partnership.partnerName}`}
            description={partnership.subtitle}
          />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="glass-card mb-10 p-6 sm:p-8"
          >
            <div className="mb-4 flex items-center gap-3">
              <Handshake className="h-8 w-8 text-[#3B82F6]" />
              <h3 className="font-heading text-xl font-bold text-white sm:text-2xl">
                {partnership.partnerName}
              </h3>
            </div>
            <p className="text-[#94A3B8] leading-relaxed">{partnership.announcement}</p>
            <ul className="mt-6 grid gap-3 sm:grid-cols-2">
              {partnership.benefits.map((benefit) => (
                <li key={benefit} className="flex items-start gap-2 text-sm text-[#94A3B8]">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#06B6D4]" />
                  {benefit}
                </li>
              ))}
            </ul>
            <p className="mt-6 border-t border-white/10 pt-6 text-sm text-[#94A3B8] leading-relaxed">
              {partnership.partnerDescription}
            </p>
          </motion.div>

          <SectionHeading
            title="Partnership Benefits"
            description="Delivering enhanced value through strategic collaboration"
            className="mb-8"
          />
          <div className="grid gap-6 md:grid-cols-3">
            {partnership.collaborationBenefits.map((item, i) => {
              const icons = [Lightbulb, Globe, Shield];
              const Icon = icons[i] ?? Lightbulb;
              return (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="glass-card p-6"
                >
                  <Icon className="mb-4 h-8 w-8 text-[#8B5CF6]" />
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
