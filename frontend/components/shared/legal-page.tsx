import Link from "next/link";

export function LegalPage({ title, updated, intro, sections }: {
  title: string;
  updated: string;
  intro: string;
  sections: { heading: string; body: React.ReactNode }[];
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 lg:px-8">
      <p className="text-sm text-[#94A3B8]">Last updated: {updated}</p>
      <h1 className="mt-2 font-heading text-3xl font-bold text-white sm:text-4xl">{title}</h1>
      <p className="mt-4 leading-relaxed text-[#CBD5E1]">{intro}</p>
      <nav aria-label="On this page" className="glass-card mt-8 p-5">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-[#94A3B8]">
          {sections.map((s, i) => (
            <li key={s.heading}><a href={`#s${i + 1}`} className="hover:text-white">{s.heading}</a></li>
          ))}
        </ol>
      </nav>
      <div className="mt-10 space-y-10">
        {sections.map((s, i) => (
          <section key={s.heading} id={`s${i + 1}`} className="scroll-mt-24">
            <h2 className="font-heading text-xl font-semibold text-white">{i + 1}. {s.heading}</h2>
            <div className="mt-3 space-y-3 leading-relaxed text-[#CBD5E1] [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-1.5">
              {s.body}
            </div>
          </section>
        ))}
      </div>
      <p className="mt-12 text-sm text-[#94A3B8]">
        See also: <Link href="/privacy" className="text-[#3B82F6] hover:underline">Privacy Policy</Link>
        {" · "}<Link href="/terms" className="text-[#3B82F6] hover:underline">Terms of Service</Link>
        {" · "}<Link href="/contact" className="text-[#3B82F6] hover:underline">Contact us</Link>
      </p>
    </div>
  );
}
