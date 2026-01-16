import { useEffect } from "react";

const DEFAULT_BRAND = "Syroce";

export function getBrandNameFromThemeCache() {
  if (typeof window === "undefined") return DEFAULT_BRAND;
  try {
    const raw = window.localStorage.getItem("theme_v1_default");
    if (!raw) return DEFAULT_BRAND;
    const parsed = JSON.parse(raw);
    const theme = parsed?.theme || parsed;
    return theme?.brand?.company_name || DEFAULT_BRAND;
  } catch {
    return DEFAULT_BRAND;
  }
}

function ensureMetaByName(name) {
  let el = document.querySelector(`meta[name='${name}']`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute("name", name);
    document.head.appendChild(el);
  }
  return el;
}

function ensureMetaByProperty(prop) {
  let el = document.querySelector(`meta[property='${prop}']`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute("property", prop);
    document.head.appendChild(el);
  }
  return el;
}

function ensureCanonicalLink() {
  let link = document.querySelector("link[rel='canonical']");
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  return link;
}

export function useSeo({
  title,
  description,
  canonicalPath,
  type = "website",
}) {
  useEffect(() => {
    if (typeof document === "undefined") return;

    const origin = window.location.origin;
    const brand = getBrandNameFromThemeCache();

    let pageTitle = title;
    if (!pageTitle) {
      pageTitle = brand;
    }

    // Apply title
    document.title = pageTitle;

    // Description
    if (description) {
      const metaDesc = ensureMetaByName("description");
      metaDesc.setAttribute("content", description);
    }

    const url = canonicalPath ? `${origin}${canonicalPath}` : window.location.href;

    // Canonical
    const linkCanonical = ensureCanonicalLink();
    linkCanonical.setAttribute("href", url);

    // Open Graph
    const ogTitle = ensureMetaByProperty("og:title");
    ogTitle.setAttribute("content", pageTitle);
    const ogDesc = ensureMetaByProperty("og:description");
    ogDesc.setAttribute("content", description || "");
    const ogUrl = ensureMetaByProperty("og:url");
    ogUrl.setAttribute("content", url);
    const ogType = ensureMetaByProperty("og:type");
    ogType.setAttribute("content", type);

    // Twitter
    const twCard = ensureMetaByName("twitter:card");
    twCard.setAttribute("content", "summary_large_image");
    const twTitle = ensureMetaByName("twitter:title");
    twTitle.setAttribute("content", pageTitle);
    const twDesc = ensureMetaByName("twitter:description");
    twDesc.setAttribute("content", description || "");
  }, [title, description, canonicalPath, type]);
}
