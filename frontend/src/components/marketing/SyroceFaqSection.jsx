import React from "react";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "../ui/accordion";

export const SyroceFaqSection = ({
  items,
  title = "Sıkça Sorulan Sorular",
  description,
  eyebrow = "SSS",
  sectionTestId = "marketing-faq-section",
}) => {
  return (
    <section className="space-y-8" data-testid={sectionTestId}>
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2563EB]" data-testid={`${sectionTestId}-eyebrow`}>
          {eyebrow}
        </p>
        <h2 className="mt-3 text-3xl font-extrabold leading-[1.08] tracking-[-0.04em] text-slate-950 sm:text-4xl lg:text-5xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`${sectionTestId}-title`}>
          {title}
        </h2>
        {description ? (
          <p className="mt-4 text-sm leading-7 text-slate-600 sm:text-base md:text-lg" data-testid={`${sectionTestId}-description`}>
            {description}
          </p>
        ) : null}
      </div>

      <div className="rounded-[2rem] border border-white/80 bg-white/92 p-4 shadow-[0_24px_80px_rgba(15,23,42,0.05)] sm:p-6" data-testid={`${sectionTestId}-accordion-wrap`}>
        <Accordion type="single" collapsible className="w-full" data-testid={`${sectionTestId}-accordion`}>
          {items.map((item, index) => (
            <AccordionItem key={item.question} value={`item-${index + 1}`} className="border-slate-200" data-testid={`${sectionTestId}-item-${index + 1}`}>
              <AccordionTrigger className="text-left text-base font-semibold text-slate-900 hover:no-underline" data-testid={`${sectionTestId}-trigger-${index + 1}`}>
                {item.question}
              </AccordionTrigger>
              <AccordionContent className="text-sm leading-7 text-slate-600" data-testid={`${sectionTestId}-content-${index + 1}`}>
                {item.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
};