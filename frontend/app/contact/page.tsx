"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Building2, Mail, MapPin, Phone, User } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { SectionHeading } from "@/components/shared/section-heading";
import { FAQSection } from "@/components/home/faq-section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { CONTACT_CONTENT } from "@/lib/site-content";
import { apiError, publicApi } from "@/services/api";

const contactSchema = z.object({
  name: z.string().trim().min(2, "Name is required").max(120, "Name is too long"),
  email: z.string().email("Valid email required"),
  subject: z.string().trim().min(3, "Subject is required").max(200, "Subject is too long"),
  message: z.string().trim().min(10, "Message must be at least 10 characters").max(5000, "Message is too long (5,000 characters max)"),
});

type ContactForm = z.infer<typeof contactSchema>;

function ContactCard({
  icon: Icon,
  label,
  children,
  index,
}: {
  icon: typeof Mail;
  label: string;
  children: React.ReactNode;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.08 }}
      className="glass-card flex gap-4 p-5"
    >
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#3B82F6]/20">
        <Icon className="h-5 w-5 text-[#3B82F6]" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-[#94A3B8]">{label}</p>
        <div className="mt-1 text-white">{children}</div>
      </div>
    </motion.div>
  );
}

export default function ContactPage() {
  const { hero, jobsnexgen, rrGroup } = CONTACT_CONTENT;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ContactForm>({
    resolver: zodResolver(contactSchema),
  });

  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  const onSubmit = async (data: ContactForm) => {
    setResult(null);
    try {
      const res = await publicApi.contact(data);
      setResult({ ok: true, text: res.data.message });
      reset();
    } catch (e) {
      setResult({ ok: false, text: apiError(e, "Sorry, your message couldn't be sent. Please email us directly.") });
    }
  };

  return (
    <div className="pb-24">
      <section className="hero-glow py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow={hero.eyebrow}
            title={hero.title}
            description={hero.description}
          />
        </div>
      </section>

      <section className="py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-12 lg:grid-cols-2">
            <div className="space-y-8">
              <div>
                <h2 className="mb-4 font-heading text-xl font-bold text-white">
                  JobsNexgen
                </h2>
                <div className="space-y-4">
                  <ContactCard icon={User} label="Contact Person" index={0}>
                    <p className="font-medium">{jobsnexgen.contactPerson}</p>
                  </ContactCard>
                  <ContactCard icon={MapPin} label="Address" index={1}>
                    <p className="text-sm leading-relaxed">{jobsnexgen.address}</p>
                  </ContactCard>
                  <ContactCard icon={Mail} label="Email Address" index={2}>
                    <a
                      href={`mailto:${jobsnexgen.email}`}
                      className="text-[#3B82F6] hover:underline"
                    >
                      {jobsnexgen.email}
                    </a>
                  </ContactCard>
                  <ContactCard icon={Phone} label="Phone" index={3}>
                    <div className="flex flex-col gap-1">
                      {jobsnexgen.phones.map((phone) => (
                        <a
                          key={phone}
                          href={`tel:${phone.replace(/\s/g, "")}`}
                          className="text-[#3B82F6] hover:underline"
                        >
                          {phone}
                        </a>
                      ))}
                    </div>
                  </ContactCard>
                </div>
                <div className="glass-card mt-6 overflow-hidden rounded-2xl">
                  <iframe
                    title="JobsNexgen office location"
                    src={`https://maps.google.com/maps?q=${encodeURIComponent(jobsnexgen.mapQuery)}&output=embed`}
                    className="h-52 w-full border-0 sm:h-64"
                    loading="lazy"
                  />
                </div>
              </div>

              <div className="border-t border-white/10 pt-8">
                <div className="mb-4 flex items-center gap-2">
                  <Building2 className="h-6 w-6 text-[#8B5CF6]" />
                  <h2 className="font-heading text-xl font-bold text-white">
                    {rrGroup.name}
                  </h2>
                </div>
                <div className="space-y-4">
                  <ContactCard icon={MapPin} label="Address" index={4}>
                    <p className="text-sm leading-relaxed">{rrGroup.address}</p>
                  </ContactCard>
                  <ContactCard icon={Building2} label="GSTIN" index={5}>
                    <p className="font-mono text-sm">{rrGroup.gstin}</p>
                  </ContactCard>
                  <ContactCard icon={Building2} label="Services" index={6}>
                    <div className="flex flex-wrap gap-2">
                      {rrGroup.services.map((s) => (
                        <Badge
                          key={s}
                          className="border-0 bg-[#8B5CF6]/20 text-[#8B5CF6]"
                        >
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </ContactCard>
                  <ContactCard icon={Phone} label="Contact" index={7}>
                    <div className="flex flex-col gap-1">
                      {rrGroup.phones.map((phone) => (
                        <a
                          key={phone}
                          href={`tel:${phone.replace(/\s/g, "")}`}
                          className="text-[#8B5CF6] hover:underline"
                        >
                          {phone}
                        </a>
                      ))}
                    </div>
                  </ContactCard>
                  <ContactCard icon={Mail} label="Email" index={8}>
                    <a
                      href={`mailto:${rrGroup.email}`}
                      className="break-all text-[#8B5CF6] hover:underline"
                    >
                      {rrGroup.email}
                    </a>
                  </ContactCard>
                </div>
                <div className="glass-card mt-6 overflow-hidden rounded-2xl">
                  <iframe
                    title="RR Group office location"
                    src={`https://maps.google.com/maps?q=${encodeURIComponent(rrGroup.mapQuery)}&output=embed`}
                    className="h-52 w-full border-0 sm:h-64"
                    loading="lazy"
                  />
                </div>
              </div>
            </div>

            <motion.form
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              onSubmit={handleSubmit(onSubmit)}
              className="glass-card h-fit space-y-5 p-6 sm:p-8 lg:sticky lg:top-24"
            >
              <div>
                <h3 className="font-heading text-lg font-bold text-white">
                  Send us a message
                </h3>
                <p className="mt-1 text-sm text-[#94A3B8]">
                  We typically respond within 48 hours.
                </p>
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    {...register("name")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {errors.name && (
                    <p className="mt-1 text-xs text-[#EF4444]">{errors.name.message}</p>
                  )}
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    {...register("email")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {errors.email && (
                    <p className="mt-1 text-xs text-[#EF4444]">{errors.email.message}</p>
                  )}
                </div>
              </div>
              <div>
                <Label htmlFor="subject">Subject</Label>
                <Input
                  id="subject"
                  {...register("subject")}
                  className="mt-1.5 border-white/10 bg-white/5"
                />
                {errors.subject && (
                  <p className="mt-1 text-xs text-[#EF4444]">{errors.subject.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="message">Message</Label>
                <Textarea
                  id="message"
                  rows={5}
                  {...register("message")}
                  className="mt-1.5 border-white/10 bg-white/5"
                />
                {errors.message && (
                  <p className="mt-1 text-xs text-[#EF4444]">{errors.message.message}</p>
                )}
              </div>
              {result && (
                <p
                  role="status"
                  className={`rounded-lg px-3 py-2 text-sm ${result.ok ? "bg-[#22C55E]/10 text-[#4ADE80]" : "bg-[#EF4444]/10 text-[#F87171]"}`}
                >
                  {result.text}
                </p>
              )}
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
              >
                {isSubmitting ? "Sending..." : "Send Message"}
              </Button>
              <p className="text-center text-xs text-[#94A3B8]">
                Or email us directly at{" "}
                <Link
                  href={`mailto:${jobsnexgen.email}`}
                  className="text-[#3B82F6] hover:underline"
                >
                  {jobsnexgen.email}
                </Link>
              </p>
            </motion.form>
          </div>
        </div>
      </section>

      <FAQSection />
    </div>
  );
}
