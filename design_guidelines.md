{
  "design_system_name": "Agency CRM – Hotel Contacts Tab Extension",
  "app_context": {
    "module": "HotelContactsTab (read‑only)",
    "location": "AgencyHotelDetailPage > CRM tabs",
    "primary_users": ["Agency managers", "Reservation/ops agents"],
    "key_tasks": [
      "Scan and search contacts quickly",
      "Trigger actions: Call, WhatsApp, Email, Copy",
      "Trust info density with strong readability in dark/light modes"
    ],
    "success_criteria": [
      "<200ms perceived response for search (client-side filter)",
      "Zero mis-clicks via clear affordances and focus states",
      "WCAG AA contrast for all text and icons"
    ]
  },

  "brand_attributes": ["professional", "reliable", "calm", "premium", "B2B-first"],

  "typography": {
    "font_stack": {
      "heading": "'Space Grotesk', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'",
      "body": "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans'"
    },
    "webfont_includes": [
      "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap",
      "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ],
    "text_scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "h3": "text-base md:text-lg font-semibold tracking-tight",
      "body": "text-sm md:text-base leading-6",
      "small": "text-xs md:text-sm"
    },
    "usage": {
      "headings": "Use Space Grotesk for tab title and toolbar labels to add distinctive premium tone.",
      "body": "Use Inter for table cells, helper text, empty states for maximum readability.",
      "numbers": "Use tabular-nums for columns like phone numbers and dates (Tailwind: font-mono tabular-nums if needed)."
    }
  },

  "color_system": {
    "note": "Aligns with existing tokens in src/index.css (:root and .dark). Extends with contact‑action semantics.",
    "semantic_tokens": {
      "light": {
        "--background": "220 33% 99%",
        "--foreground": "224 26% 16%",
        "--primary": "220 65% 22%",
        "--primary-foreground": "210 40% 98%",
        "--secondary": "220 20% 96%",
        "--muted": "220 20% 96%",
        "--accent": "220 25% 94%",
        "--border": "220 18% 88%",
        "--ring": "220 65% 22%",
        "--contact-call": "152 71% 35%",
        "--contact-whatsapp": "151 65% 36%",
        "--contact-email": "196 62% 42%",
        "--contact-copy": "224 12% 40%"
      },
      "dark": {
        "--background": "224 30% 6%",
        "--foreground": "210 40% 98%",
        "--primary": "220 70% 60%",
        "--primary-foreground": "224 30% 6%",
        "--secondary": "223 22% 14%",
        "--muted": "223 22% 14%",
        "--accent": "223 22% 14%",
        "--border": "223 20% 18%",
        "--ring": "220 70% 60%",
        "--contact-call": "151 55% 48%",
        "--contact-whatsapp": "151 60% 44%",
        "--contact-email": "196 62% 55%",
        "--contact-copy": "224 10% 68%"
      }
    },
    "usage_rules": [
      "Use --primary for selected states and toolbar primary controls",
      "Row hover: subtle overlay using bg-accent/50 on hover",
      "Action icon tints: call = --contact-call, whatsapp = --contact-whatsapp, email = --contact-email, copy = --contact-copy",
      "Avoid saturated/dark gradients; prefer solids. If gradient needed for header chip, keep under 20% viewport and low saturation"
    ]
  },

  "data_table_styling": {
    "density": "Comfortable by default. Use lg:compact at >1024px via tighter paddings.",
    "header": "Sticky header with backdrop-blur supports long lists.",
    "row": "Hover: transition-colors shadow-none bg-accent/30; Focus-within: outline-ring",
    "zebra": "Apply odd:bg-muted/30 in light and odd:bg-muted/20 in dark for readability.",
    "columns": [
      {"key": "name", "min_w": "14rem", "weight": "strong"},
      {"key": "role", "min_w": "10rem"},
      {"key": "department", "min_w": "10rem"},
      {"key": "phone", "min_w": "12rem", "type": "tel"},
      {"key": "email", "min_w": "16rem", "type": "email"},
      {"key": "notes", "min_w": "14rem", "truncate": true},
      {"key": "actions", "w": "12rem", "align": "right"}
    ],
    "empty_state": "Use a neutral card with small illustration; provide primary CTA to add contact if permissions allow (else hide).",
    "pagination": "Client-side with shadcn Pagination if dataset is large; otherwise virtual scroll with sticky header."
  },

  "layout_and_grid": {
    "container": "px-4 sm:px-6 lg:px-8 w-full max-w-[1400px] mx-auto",
    "toolbar": "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4",
    "table_wrapper": "relative overflow-auto rounded-lg border border-border",
    "sticky_header": "sticky top-0 z-10 bg-background/75 backdrop-blur supports-[backdrop-filter]:bg-background/60",
    "mobile_pattern": "At <640px show stacked cards: name, role, department, phone/email inline actions; preserve data-testid on each action",
    "spacing": "Use 1.5x–2x spacing compared to Notes/Tasks tabs for clarity in dense data"  
  },

  "components": {
    "shadcn": [
      {"name": "Table", "import": "./components/ui/table"},
      {"name": "Input", "import": "./components/ui/input"},
      {"name": "Button", "import": "./components/ui/button"},
      {"name": "Badge", "import": "./components/ui/badge"},
      {"name": "Tooltip", "import": "./components/ui/tooltip"},
      {"name": "DropdownMenu", "import": "./components/ui/dropdown-menu"},
      {"name": "Separator", "import": "./components/ui/separator"},
      {"name": "ScrollArea", "import": "./components/ui/scroll-area"},
      {"name": "Avatar", "import": "./components/ui/avatar"},
      {"name": "Pagination", "import": "./components/ui/pagination"},
      {"name": "Skeleton", "import": "./components/ui/skeleton"},
      {"name": "Sonner (toasts)", "import": "./components/ui/sonner"}
    ],
    "third_party": [
      {"name": "lucide-react", "reason": "action icons (Phone, MessageCircle, Mail, Copy, Search)", "install": "npm i lucide-react"}
    ]
  },

  "buttons": {
    "style_family": "Professional / Corporate",
    "shape": "rounded-md (var(--radius))",
    "motion": "transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "variants": [
      {
        "name": "primary",
        "class": "bg-primary text-primary-foreground hover:bg-primary/90"
      },
      {
        "name": "ghost",
        "class": "hover:bg-accent/60 text-foreground"
      },
      {
        "name": "destructive",
        "class": "bg-destructive text-destructive-foreground hover:bg-destructive/90"
      }
    ],
    "sizes": {
      "sm": "h-8 px-3 text-xs",
      "md": "h-9 px-3 text-sm",
      "lg": "h-10 px-4 text-sm"
    }
  },

  "micro_interactions": {
    "row_hover": "transition-colors duration-150 hover:bg-accent/30",
    "icon_button": "transition-colors duration-150 hover:text-foreground focus-visible:ring-2",
    "toolbar_reveal": "fade-in via opacity-0 -> opacity-100 on mount using Tailwind animate-[fadeIn_.2s_ease-out] or framer-motion (optional)",
    "no_universal_transition": true
  },

  "accessibility": {
    "contrast": "Maintain AA for all combinations; do not reduce opacity of essential text below 0.8.",
    "focus": "Use ring theme for keyboard focus; ensure tab order: search -> table header -> rows -> actions",
    "aria": [
      "aria-label on action buttons: 'Call {name}', 'WhatsApp {name}', 'Email {name}', 'Copy {field}'",
      "role='row' and role='columnheader' as provided by shadcn Table"
    ],
    "testing_ids": "All interactive and key informational elements MUST include data-testid in kebab-case (e.g., data-testid='contacts-search-input', 'row-call-button', 'row-email-link')."
  },

  "tokens_css": {
    "additions_to_index_css": "@layer base { :root { --contact-call: 152 71% 35%; --contact-whatsapp: 151 65% 36%; --contact-email: 196 62% 42%; --contact-copy: 224 12% 40%; } .dark { --contact-call: 151 55% 48%; --contact-whatsapp: 151 60% 44%; --contact-email: 196 62% 55%; --contact-copy: 224 10% 68%; } }",
    "utility_examples": [
      "text-[hsl(var(--contact-email))]",
      "hover:bg-[hsl(var(--accent))]/60",
      "focus-visible:ring-[hsl(var(--ring))]"
    ]
  },

  "example_component_scaffold_jsx": {
    "file": "src/features/agency/hotels/HotelContactsTab.jsx",
    "snippet": "import React, { useMemo, useState } from 'react';\nimport { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';\nimport { Input } from '../../components/ui/input';\nimport { Button } from '../../components/ui/button';\nimport { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip';\nimport { ScrollArea } from '../../components/ui/scroll-area';\nimport { Toaster, toast } from '../../components/ui/sonner';\nimport { Phone, MessageCircle, Mail, Copy, Search } from 'lucide-react';\n\nexport default function HotelContactsTab({ contacts = [] }) {\n  const [term, setTerm] = useState('');\n  const filtered = useMemo(() => {\n    const t = term.toLowerCase();\n    return contacts.filter(c => [c.name, c.role, c.department, c.phone, c.email].filter(Boolean).some(v => String(v).toLowerCase().includes(t)));\n  }, [contacts, term]);\n\n  const copyToClipboard = (value) => {\n    navigator.clipboard?.writeText(value);\n    toast.success('Copied to clipboard');\n  };\n\n  const telHref = (p='') => `tel:${String(p).replace(/[^+\d]/g,'')}`;\n  const waHref = (p='') => { const n = String(p).replace(/[^+\d]/g,''); return `https://wa.me/${n}`; };\n  const mailHref = (e='') => `mailto:${e}`;\n\n  return (\n    <div className=\"px-4 sm:px-6 lg:px-8\">\n      <Toaster />\n      <div className=\"flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4\">\n        <div className=\"relative w-full sm:max-w-sm\">\n          <Search className=\"absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground\" />\n          <Input\n            data-testid=\"contacts-search-input\"\n            value={term}\n            onChange={(e)=>setTerm(e.target.value)}\n            placeholder=\"Search name, phone, email...\"\n            className=\"pl-9\"\n          />\n        </div>\n      </div>\n\n      <div className=\"relative overflow-auto rounded-lg border border-border\">\n        <Table>\n          <TableHeader className=\"sticky top-0 z-10 bg-background/75 backdrop-blur supports-[backdrop-filter]:bg-background/60\">\n            <TableRow>\n              <TableHead>Name</TableHead>\n              <TableHead>Role</TableHead>\n              <TableHead>Department</TableHead>\n              <TableHead>Phone</TableHead>\n              <TableHead>Email</TableHead>\n              <TableHead className=\"text-right\">Actions</TableHead>\n            </TableRow>\n          </TableHeader>\n          <TableBody>\n            {filtered.length === 0 ? (\n              <TableRow>\n                <TableCell colSpan={6} className=\"py-10 text-center text-muted-foreground\" data-testid=\"contacts-empty-state\">\n                  No contacts match your search.\n                </TableCell>\n              </TableRow>\n            ) : (\n              filtered.map((c) => (\n                <TableRow key={c.id || c.email} className=\"odd:bg-muted/20 hover:bg-accent/30 transition-colors\">\n                  <TableCell className=\"whitespace-nowrap font-medium\">{c.name}</TableCell>\n                  <TableCell className=\"text-muted-foreground\">{c.role}</TableCell>\n                  <TableCell className=\"text-muted-foreground\">{c.department}</TableCell>\n                  <TableCell className=\"font-mono tabular-nums\">{c.phone}</TableCell>\n                  <TableCell className=\"truncate max-w-[16rem]\">{c.email}</TableCell>\n                  <TableCell className=\"text-right\">\n                    <div className=\"inline-flex items-center gap-1.5\">\n                      <TooltipProvider delayDuration={200}>\n                        <Tooltip>\n                          <TooltipTrigger asChild>\n                            <Button data-testid=\"row-call-button\" variant=\"ghost\" size=\"sm\" className=\"text-[hsl(var(--contact-call))]\" asChild>\n                              <a href={telHref(c.phone)} aria-label={`Call ${c.name}`}>\n                                <Phone className=\"h-4 w-4\" />\n                              </a>\n                            </Button>\n                          </TooltipTrigger>\n                          <TooltipContent>Call</TooltipContent>\n                        </Tooltip>\n                        <Tooltip>\n                          <TooltipTrigger asChild>\n                            <Button data-testid=\"row-whatsapp-button\" variant=\"ghost\" size=\"sm\" className=\"text-[hsl(var(--contact-whatsapp))]\" asChild>\n                              <a href={waHref(c.phone)} target=\"_blank\" rel=\"noreferrer\" aria-label={`WhatsApp ${c.name}`}>\n                                <MessageCircle className=\"h-4 w-4\" />\n                              </a>\n                            </Button>\n                          </TooltipTrigger>\n                          <TooltipContent>WhatsApp</TooltipContent>\n                        </Tooltip>\n                        <Tooltip>\n                          <TooltipTrigger asChild>\n                            <Button data-testid=\"row-email-button\" variant=\"ghost\" size=\"sm\" className=\"text-[hsl(var(--contact-email))]\" asChild>\n                              <a href={mailHref(c.email)} aria-label={`Email ${c.name}`}>\n                                <Mail className=\"h-4 w-4\" />\n                              </a>\n                            </Button>\n                          </TooltipTrigger>\n                          <TooltipContent>Email</TooltipContent>\n                        </Tooltip>\n                        <Tooltip>\n                          <TooltipTrigger asChild>\n                            <Button data-testid=\"row-copy-button\" variant=\"ghost\" size=\"sm\" className=\"text-[hsl(var(--contact-copy))]\" onClick={() => copyToClipboard(`${c.name} | ${c.phone} | ${c.email}`)} aria-label={`Copy ${c.name}`}>\n                              <Copy className=\"h-4 w-4\" />\n                            </Button>\n                          </TooltipTrigger>\n                          <TooltipContent>Copy</TooltipContent>\n                        </Tooltip>\n                      </TooltipProvider>\n                    </div>\n                  </TableCell>\n                </TableRow>\n              ))\n            )}\n          </TableBody>\n        </Table>\n      </div>\n    </div>\n  );\n}\n"
  },

  "iconography": {
    "library": "lucide-react",
    "icons": {
      "search": "Search",
      "call": "Phone",
      "whatsapp": "MessageCircle",
      "email": "Mail",
      "copy": "Copy"
    }
  },

  "testing_strategy": {
    "principles": [
      "Use data-testid on toolbar, search input, table, each action, empty state, and confirmation toasts",
      "Prefer role/accessible name for end-to-end tests but keep testids stable"
    ],
    "ids": [
      "contacts-search-input",
      "contacts-table",
      "contacts-empty-state",
      "row-call-button",
      "row-whatsapp-button",
      "row-email-button",
      "row-copy-button"
    ]
  },

  "light_dark_mode": {
    "support": "Native via Tailwind and CSS variables already defined in index.css",
    "guidance": [
      "Do not invert icons aggressively; rely on currentColor against text-foreground",
      "Use bg-background and border-border consistently; avoid hardcoded hex",
      "Keep hover/focus states in dark at +8–12% lightness shifts only"
    ]
  },

  "performance": {
    "lists": "Memoize filtered data; avoid re-rendering all rows by memoizing row components if dataset > 500",
    "virtualization": "If contacts exceed 1k, integrate react-virtualized or @tanstack/react-virtual; keep shadcn Table semantics"
  },

  "component_path": [
    {"name": "Table", "path": "./components/ui/table.jsx"},
    {"name": "Input", "path": "./components/ui/input.jsx"},
    {"name": "Button", "path": "./components/ui/button.jsx"},
    {"name": "Badge", "path": "./components/ui/badge.jsx"},
    {"name": "Tooltip", "path": "./components/ui/tooltip.jsx"},
    {"name": "DropdownMenu", "path": "./components/ui/dropdown-menu.jsx"},
    {"name": "Separator", "path": "./components/ui/separator.jsx"},
    {"name": "ScrollArea", "path": "./components/ui/scroll-area.jsx"},
    {"name": "Avatar", "path": "./components/ui/avatar.jsx"},
    {"name": "Pagination", "path": "./components/ui/pagination.jsx"},
    {"name": "Skeleton", "path": "./components/ui/skeleton.jsx"},
    {"name": "Sonner", "path": "./components/ui/sonner.jsx"}
  ],

  "image_urls": [
    {
      "url": "https://images.unsplash.com/photo-1611055157256-7fed5fc880ca?crop=entropy&cs=srgb&fm=jpg&q=85",
      "description": "Dark minimal foliage – subtle header/empty state illustration",
      "category": "empty-state"
    },
    {
      "url": "https://images.unsplash.com/photo-1721549369164-2fd07f795ce4?crop=entropy&cs=srgb&fm=jpg&q=85",
      "description": "Abstract black curved surfaces – section background overlay (max 20% viewport)",
      "category": "decorative-section"
    },
    {
      "url": "https://images.unsplash.com/photo-1747113225475-8592c238cf08?crop=entropy&cs=srgb&fm=jpg&q=85",
      "description": "Minimal illuminated frame – use sparingly in marketing header, not in table",
      "category": "marketing-hero"
    }
  ],

  "instructions_to_main_agent": [
    "1) Add the provided Google Fonts <link> tags to index.html and set fonts via Tailwind 'font-[custom]' if configured.",
    "2) Extend color tokens by pasting tokens_css.additions_to_index_css into src/index.css under an existing @layer base block.",
    "3) Create src/features/agency/hotels/HotelContactsTab.jsx using example_component_scaffold_jsx.snippet (adjust imports to your actual relative paths).",
    "4) On AgencyHotelDetailPage, register a new Tab trigger 'Contacts' and mount <HotelContactsTab contacts={hotel.contacts} />.",
    "5) Ensure all buttons/links/inputs include data-testid attributes following kebab-case role naming.",
    "6) Icons: npm i lucide-react, then import from 'lucide-react'.",
    "7) Toasts: Ensure <Toaster /> from ./components/ui/sonner.jsx exists at layout root or within Contacts tab as in scaffold.",
    "8) Keep sticky header styles and overflow-auto wrapper; verify on mobile that table converts to stacked cards if you implement responsive card layout.",
    "9) Enforce gradient restriction rules and avoid universal transitions. Use transition-colors only on actionable elements.",
    "10) Add e2e tests targeting data-testid values listed in testing_strategy.ids."
  ],

  "gradients_and_textures": {
    "rule": "Use gradients only for decorative section backgrounds, never for the table body. Keep below 20% viewport.",
    "allowed_example": "bg-[linear-gradient(135deg,_hsl(220_30%_12%)_0%,_hsl(223_22%_14%)_100%)] on a toolbar wrapper with 8% overlay opacity",
    "fallback": "If readability impacted, switch to solid bg-secondary"
  },

  "motion": {
    "principles": [
      "Snappy micro-interactions (100–150ms) for hover/focus",
      "Entrance: fade in table (150ms) after data resolves",
      "No parallax or heavy motion inside the data table"
    ]
  },

  "code_quality": {
    "js_only": true,
    "exports": [
      "Components must use named exports where applicable (export const Component = ...) and pages default export",
      "Follow existing project conventions in src/components/ui"
    ]
  },

  "appendix": {
    "references": [
      "Attio Dark Mode Table (Dribbble) for dark table legibility",
      "Admin templates with sticky headers and search bars as pattern confirmation"
    ],
    "notes": "Design aligns with current corporate navy palette defined in index.css; action colors add clarity without clashing."
  },

  "general_ui_ux_design_guidelines": "- You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.",

  "version": 1
}
