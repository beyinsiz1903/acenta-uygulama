import React from "react";

export const LandingSectionHeading = ({
  eyebrow,
  title,
  description,
  align = "left",
  testIdPrefix,
}) => {
  const alignmentClassName = align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl";

  return (
    <div className={alignmentClassName} data-testid={`${testIdPrefix}-wrap`}>
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#2563EB] sm:text-sm sm:tracking-[0.3em]" data-testid={`${testIdPrefix}-eyebrow`}>
        {eyebrow}
      </p>
      <h2 className="mt-4 break-words text-3xl font-extrabold leading-[1.06] tracking-[-0.04em] text-slate-950 sm:text-4xl lg:text-5xl" data-testid={`${testIdPrefix}-title`}>
        {title}
      </h2>
      <p className="mt-4 text-sm leading-7 text-slate-600 sm:text-base md:text-lg" data-testid={`${testIdPrefix}-description`}>
        {description}
      </p>
    </div>
  );
};