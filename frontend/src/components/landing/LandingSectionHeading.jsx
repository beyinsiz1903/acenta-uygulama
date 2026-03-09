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
      <p className="text-sm font-semibold uppercase tracking-[0.3em] text-[#2563EB]" data-testid={`${testIdPrefix}-eyebrow`}>
        {eyebrow}
      </p>
      <h2 className="mt-4 text-4xl font-extrabold tracking-[-0.04em] text-slate-950 sm:text-5xl" data-testid={`${testIdPrefix}-title`}>
        {title}
      </h2>
      <p className="mt-4 text-base leading-7 text-slate-600 md:text-lg" data-testid={`${testIdPrefix}-description`}>
        {description}
      </p>
    </div>
  );
};