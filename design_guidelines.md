{
  "brand_attributes": ["trustworthy", "concise", "operational", "data-first", "calm"],
  "design_personality": "Clean corporate with soft ocean accents. Card-based, roomy spacing, readable numbers, subtle motion. Matches existing Agency wizard + settlements visuals (rounded cards, muted foregrounds, lucide icons).",
  "inspiration_sources": [
    {
      "title": "Hotel Financial Management Dashboard",
      "url": "https://dribbble.com/shots/24865402-Hotel-Financial-Management-Dashboard",
      "borrow": "compact KPI cards, stacked sections, soft neutral backgrounds"
    },
    {
      "title": "Finance Management Dashboard",
      "url": "https://dribbble.com/shots/26713863-Finance-Management-Dashboard",
      "borrow": "clear monetary hierarchy, number emphasis"
    },
    {
      "title": "Behance finance dashboards collection",
      "url": "https://www.behance.net/search/projects/financial%20dashboard%20ui%20design?locale=en_US",
      "borrow": "filter bars with presets + ranges, status badges in tables"
    }
  ],
  "color_system": {
    "tokens": {
      "primary": "hsl(var(--primary))",
      "background": "hsl(var(--background))",
      "foreground": "hsl(var(--foreground))",
      "muted": "hsl(var(--muted))",
      "muted-foreground": "hsl(var(--muted-foreground))",
      "border": "hsl(var(--border))",
      "success": "hsl(158 55% 40%)",
      "success-foreground": "hsl(210 40% 98%)",
      "warning": "hsl(38 92% 50%)",
      "warning-foreground": "hsl(224 26% 16%)",
      "info": "hsl(196 62% 42%)",
      "info-foreground": "hsl(210 40% 98%)"
    },
    "index_css_patch": {
      "add_to_:root": "--success: 158 55% 40%;\n--success-foreground: 210 40% 98%;\n--warning: 38 92% 50%;\n--warning-foreground: 224 26% 16%;\n--info: 196 62% 42%;\n--info-foreground: 210 40% 98%;",
      "add_to_.dark": "--success: 158 55% 46%;\n--success-foreground: 224 30% 6%;\n--warning: 38 92% 56%;\n--warning-foreground: 224 30% 6%;\n--info: 196 62% 55%;\n--info-foreground: 224 30% 6%;"
    },
    "usage": {
      "finance_accent": "Use chart-2 (teal/blue) and success tokens for Paid, destructive for Unpaid, warning for Partially paid.",
      "cards": "White/secondary surfaces only, never gradient on content cards.",
      "gradients": "Only for section headers/hero ribbons if used; keep mild ocean tints (teal/blue) and below 20% viewport."
    },
    "gradients_recommended": [
      "from-[hsl(196_62%_96%)] via-[hsl(168_55%_96%)] to-[hsl(220_33%_98%)]",
      "from-[hsl(168_55%_95%)] to-[hsl(196_62%_95%)]"
    ]
  },
  "typography": {
    "fonts": {
      "headings": "Space Grotesk, Inter, system-ui, sans-serif",
      "body": "Inter, system-ui, sans-serif",
      "numeric_emphasis": "Space Grotesk for numerals (tabular-nums)"
    },
    "load": "Add Google Fonts: <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap\" rel=\"stylesheet\"> and set body { font-family: Inter; } headings classes use Space Grotesk.",
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight",
      "h2": "text-base md:text-lg font-semibold",
      "body": "text-sm md:text-base",
      "small": "text-xs text-muted-foreground"
    },
    "helpers": {
      "num_class": "font-[\'Space_Grotesk\'] tabular-nums",
      "currency_format": "Prefer ₺ with narrow no-break space (e.g., ₺ 12.345,67)."
    }
  },
  "layout_grid": {
    "page_padding": "px-4 sm:px-6 lg:px-8",
    "section_vspace": "py-4 sm:py-6 lg:py-8",
    "grid": {
      "kpi": "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
      "two_col": "grid grid-cols-1 lg:grid-cols-2 gap-6",
      "twelve_col": "grid grid-cols-1 md:grid-cols-12 gap-6"
    },
    "cards": "rounded-[var(--radius)] border bg-card text-card-foreground shadow-sm"
  },
  "components": {
    "finance_summary_card_in_booking_drawer": {
      "description": "Compact financial overview with inline status update and self-billing PDF.",
      "data_testids": [
        "finance-summary-card",
        "payment-status-select",
        "payment-status-save-button",
        "self-billing-download-button"
      ],
      "structure": [
        "Header: title + small context badge",
        "Rows: Gross, Commission (% + amount), Net to Hotel, Payment Status",
        "Actions: Select (unpaid/partially_paid/paid) + Save, Secondary PDF button"
      ],
      "jsx_scaffold": "import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './components/ui/card';\nimport { Badge } from './components/ui/badge';\nimport { Separator } from './components/ui/separator';\nimport { Button } from './components/ui/button';\nimport { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from './components/ui/select';\nimport { FileText, Percent } from 'lucide-react';\n\nexport const FinanceSummaryCard = ({ grossTRY, commissionPct, commissionTRY, netToHotelTRY, paymentStatus, onStatusChange, onSave, onDownloadPdf }) => {\n  return (\n    <Card data-testid=\"finance-summary-card\" className=\"bg-card/80 backdrop-blur-sm\">\n      <CardHeader className=\"pb-2\">\n        <div className=\"flex items-center justify-between\">\n          <CardTitle className=\"text-base md:text-lg\">Finansal Özet</CardTitle>\n          <Badge variant=\"secondary\" className=\"uppercase tracking-wide\">Snapshot</Badge>\n        </div>\n      </CardHeader>\n      <CardContent className=\"space-y-3\">\n        <div className=\"flex items-center justify-between\">\n          <span className=\"text-sm text-muted-foreground\">Brüt</span>\n          <span className=\"font-semibold font-['Space_Grotesk'] tabular-nums\">{grossTRY}</span>\n        </div>\n        <div className=\"flex items-start justify-between\">\n          <div className=\"flex items-center gap-2\">\n            <span className=\"text-sm text-muted-foreground\">Komisyon</span>\n            <Percent className=\"h-3.5 w-3.5 text-muted-foreground\" />\n          </div>\n          <div className=\"text-right\">\n            <div className=\"font-semibold font-['Space_Grotesk'] tabular-nums\">{commissionTRY}</div>\n            <div className=\"text-xs text-muted-foreground\">{commissionPct}%</div>\n          </div>\n        </div>\n        <Separator />\n        <div className=\"flex items-center justify-between\">\n          <span className=\"text-sm text-muted-foreground\">Otele Net</span>\n          <span className=\"font-semibold font-['Space_Grotesk'] tabular-nums\">{netToHotelTRY}</span>\n        </div>\n        <div className=\"flex items-center justify-between\">\n          <span className=\"text-sm text-muted-foreground\">Ödeme Durumu</span>\n          <Badge variant=\"outline\" className=\"capitalize\">{paymentStatus.replace('_',' ')}</Badge>\n        </div>\n      </CardContent>\n      <CardFooter className=\"flex flex-col sm:flex-row gap-2 justify-between\">\n        <div className=\"flex-1\">\n          <Select value={paymentStatus} onValueChange={onStatusChange}>\n            <SelectTrigger data-testid=\"payment-status-select\" className=\"w-full\">\n              <SelectValue placeholder=\"Ödeme durumu seçin\" />\n            </SelectTrigger>\n            <SelectContent align=\"end\">\n              <SelectItem value=\"unpaid\">Unpaid</SelectItem>\n              <SelectItem value=\"partially_paid\">Partially Paid</SelectItem>\n              <SelectItem value=\"paid\">Paid</SelectItem>\n            </SelectContent>\n          </Select>\n        </div>\n        <div className=\"flex gap-2\">\n          <Button data-testid=\"payment-status-save-button\" onClick={onSave} className=\"\">Kaydet</Button>\n          <Button data-testid=\"self-billing-download-button\" variant=\"outline\" onClick={onDownloadPdf} className=\"\">\n            <FileText className=\"h-4 w-4 mr-2\" /> PDF\n          </Button>\n        </div>\n      </CardFooter>\n    </Card>\n  );\n};"
    },
    "agency_reports_page": {
      "hierarchy": [
        "Header: title + period summary",
        "Filter bar: presets (last N days) + date range + refresh",
        "KPI grid: Total Bookings, Total Gross, Total Commission, Paid/Unpaid",
        "Breakdown table: by payment_status or by day"
      ],
      "filter_bar_scaffold": "import { Button } from './components/ui/button';\nimport { Popover, PopoverContent, PopoverTrigger } from './components/ui/popover';\nimport { Calendar } from './components/ui/calendar';\nimport { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from './components/ui/select';\nimport { Calendar as CalendarIcon, RefreshCw } from 'lucide-react';\n\nexport const ReportsFilterBar = ({ preset, onPresetChange, range, onRangeChange, onRefresh }) => {\n  return (\n    <div className=\"flex flex-col sm:flex-row items-stretch sm:items-center gap-2\">\n      <Select value={preset} onValueChange={onPresetChange}>\n        <SelectTrigger data-testid=\"reports-preset-select\" className=\"w-full sm:w-44\">\n          <SelectValue placeholder=\"Son N gün\" />\n        </SelectTrigger>\n        <SelectContent>\n          <SelectItem value=\"7\">Son 7 gün</SelectItem>\n          <SelectItem value=\"14\">Son 14 gün</SelectItem>\n          <SelectItem value=\"30\">Son 30 gün</SelectItem>\n          <SelectItem value=\"custom\">Özel tarih</SelectItem>\n        </SelectContent>\n      </Select>\n      <Popover>\n        <PopoverTrigger asChild>\n          <Button variant=\"outline\" className=\"justify-start\" data-testid=\"reports-date-range-button\">\n            <CalendarIcon className=\"h-4 w-4 mr-2\" /> Tarih Aralığı\n          </Button>\n        </PopoverTrigger>\n        <PopoverContent align=\"start\" className=\"p-0\">\n          <Calendar mode=\"range\" selected={range} onSelect={onRangeChange} numberOfMonths={2} />\n        </PopoverContent>\n      </Popover>\n      <Button data-testid=\"agency-finance-refresh-button\" onClick={onRefresh}\n        className=\"\"><RefreshCw className=\"h-4 w-4 mr-2\"/>Yenile</Button>\n    </div>\n  );\n};",
      "kpi_cards_scaffold": "import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';\nimport { Badge } from './components/ui/badge';\nimport { Wallet, Percent, FileText, CheckCircle2 } from 'lucide-react';\n\nexport const KPIGrid = ({ items }) => {\n  // items: [{label, value, delta, icon}]\n  const IconMap = { Wallet, Percent, FileText, CheckCircle2 };\n  return (\n    <div className=\"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4\">\n      {items.map((it) => {\n        const Ico = IconMap[it.icon] || Wallet;\n        return (\n          <Card key={it.label}>\n            <CardHeader className=\"pb-1\"><CardTitle className=\"text-sm text-muted-foreground\">{it.label}</CardTitle></CardHeader>\n            <CardContent className=\"flex items-end justify-between\">\n              <div className=\"text-2xl font-semibold font-['Space_Grotesk'] tabular-nums\">{it.value}</div>\n              {it.delta ? <Badge variant=\"outline\" className=\"text-xs\">{it.delta}</Badge> : null}\n              <Ico className=\"h-4 w-4 text-muted-foreground\" />\n            </CardContent>\n          </Card>\n        );\n      })}\n    </div>\n  );\n};",
      "table_scaffold": "import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from './components/ui/table';\nimport { Badge } from './components/ui/badge';\n\nconst StatusBadge = ({ value }) => {\n  const map = { paid: 'success', unpaid: 'destructive', partially_paid: 'warning' };\n  const tone = map[value] || 'secondary';\n  const cls = tone === 'success' ? 'bg-[hsl(var(--success))] text-[hsl(var(--success-foreground))]' :\n              tone === 'warning' ? 'bg-[hsl(var(--warning))] text-[hsl(var(--warning-foreground))]' :\n              tone === 'destructive' ? 'bg-destructive text-destructive-foreground' : 'bg-secondary';\n  return <Badge className=\"capitalize\" variant=\"outline\"><span className=\"sr-only\">status</span><span>{value.replace('_',' ')}</span></Badge>\n}\n\nexport const PaymentsBreakdownTable = ({ rows }) => (\n  <div className=\"overflow-x-auto\">\n    <Table data-testid=\"agency-reports-table\">\n      <TableHeader>\n        <TableRow>\n          <TableHead>Tarih</TableHead>\n          <TableHead>Acenta</TableHead>\n          <TableHead className=\"text-right\">Brüt</TableHead>\n          <TableHead className=\"text-right\">Komisyon</TableHead>\n          <TableHead className=\"text-right\">Net</TableHead>\n          <TableHead>Durum</TableHead>\n        </TableRow>\n      </TableHeader>\n      <TableBody>\n        {rows.map((r) => (\n          <TableRow key={r.id}>\n            <TableCell>{r.date}</TableCell>\n            <TableCell>{r.agency}</TableCell>\n            <TableCell className=\"text-right font-['Space_Grotesk'] tabular-nums\">{r.gross}</TableCell>\n            <TableCell className=\"text-right font-['Space_Grotesk'] tabular-nums\">{r.commission}</TableCell>\n            <TableCell className=\"text-right font-['Space_Grotesk'] tabular-nums\">{r.net}</TableCell>\n            <TableCell><StatusBadge value={r.status} /></TableCell>\n          </TableRow>\n        ))}\n      </TableBody>\n    </Table>\n  </div>\n);"
    },
    "hotel_dashboard_page": {
      "hierarchy": [
        "Header with period select",
        "Two columns: left totals (gross, net to hotel), right agency strip chart",
        "Bottom: paid/unpaid summary tiles"
      ],
      "period_select": "Use Select with data-testid=\"hotel-dashboard-period-select\" (7/14/30/custom).",
      "css_strip_chart_scaffold": "// Data shape: [{agency:'A', gross: 120000, net: 90000, percent: 65}]\nexport const AgencyStripChart = ({ data }) => (\n  <div className=\"space-y-3\">\n    {data.map((d) => (\n      <div key={d.agency} className=\"\">\n        <div className=\"flex justify-between text-xs text-muted-foreground mb-1\">\n          <span>{d.agency}</span><span className=\"font-['Space_Grotesk'] tabular-nums\">{d.percent}%</span>\n        </div>\n        <div className=\"h-3 w-full bg-secondary rounded-full overflow-hidden\" role=\"img\" aria-label=\"agency share\">\n          <div className=\"h-full bg-[hsl(196_62%_42%)]\" style={{ width: `${d.percent}%` }} />\n        </div>\n      </div>\n    ))}\n  </div>\n);",
      "totals_scaffold": "import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';\n\nexport const Totals = ({ gross, net }) => (\n  <div className=\"grid grid-cols-1 sm:grid-cols-2 gap-4\">\n    <Card>\n      <CardHeader className=\"pb-1\"><CardTitle className=\"text-sm text-muted-foreground\">Toplam Brüt</CardTitle></CardHeader>\n      <CardContent className=\"text-2xl font-semibold font-['Space_Grotesk'] tabular-nums\">{gross}</CardContent>\n    </Card>\n    <Card>\n      <CardHeader className=\"pb-1\"><CardTitle className=\"text-sm text-muted-foreground\">Otele Net</CardTitle></CardHeader>\n      <CardContent className=\"text-2xl font-semibold font-['Space_Grotesk'] tabular-nums\">{net}</CardContent>\n    </Card>\n  </div>\n);"
    },
    "empty_error_states": {
      "icons": "Use lucide-react: Inbox, AlertTriangle, Search.",
      "empty_state": "Centered card with soft ocean background image (low opacity), short copy, and a primary CTA to adjust filters.",
      "error_state": "Alert component with descriptive message and retry button."
    },
    "buttons": {
      "style": "Professional / Corporate",
      "variants": ["primary", "secondary", "outline", "ghost"],
      "sizes": ["sm", "md", "lg"],
      "motion": "hover: slight shade shift (bg/10%), focus-visible:ring-2 ring-[hsl(var(--ring))], active:scale-[0.99] (only on buttons)"
    }
  },
  "micro_interactions": {
    "libraries": ["framer-motion"],
    "install": "npm i framer-motion",
    "usage": [
      "Fade+slide in sections on mount (y:8, duration:0.25)",
      "Subtle scale on KPI card hover (scale:1.01)",
      "Do not animate layout shifts of long tables"
    ],
    "code_snippet": "import { motion } from 'framer-motion';\nexport const FadeIn = ({ children, className }) => (\n  <motion.div initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:0.25}} className={className}>{children}</motion.div>\n);"
  },
  "accessibility": {
    "contrast": "Maintain WCAG AA: text on secondary/muted must be foreground >= 4.5:1",
    "focus": "Use focus-visible:ring-2 ring-[hsl(var(--ring))] ring-offset-2",
    "screen_reader": "sr-only labels for icons-only buttons and chart bars",
    "numbers": "Use tabular-nums for columns to avoid jitter",
    "i18n": "Payment statuses: unpaid, partially_paid, paid (backend-driven)"
  },
  "data_testids": {
    "naming": "kebab-case describing role not appearance",
    "required": [
      "finance-summary-card",
      "payment-status-select",
      "payment-status-save-button",
      "self-billing-download-button",
      "agency-finance-refresh-button",
      "hotel-dashboard-period-select",
      "reports-preset-select",
      "reports-date-range-button",
      "agency-reports-table",
      "empty-state-cta",
      "error-retry-button"
    ]
  },
  "pages_structure": {
    "BookingDetailDrawer_financial_summary": {
      "layout": "Stacked rows, then actions row. Fit within existing drawer. Respect drawer padding.",
      "spacing": "content space-y-3; footer gap-2; larger numbers for monetary values",
      "typography": "labels text-sm text-muted-foreground; values Space Grotesk 600"
    },
    "AgencyReportsPage": {
      "sections": ["Header", "FilterBar", "KPIGrid", "BreakdownTable"],
      "responsive": "mobile single column; KPI grid 1/2/4 as viewport grows",
      "empty_state_copy": "Seçilen tarih aralığında veri bulunamadı. Filtreleri genişletmeyi deneyin."
    },
    "HotelDashboardPage": {
      "sections": ["Header with period select", "Totals", "AgencyStripChart", "Paid/Unpaid tiles"],
      "responsive": "Totals above, chart below on mobile; two columns on lg"
    }
  },
  "image_urls": [
    {
      "url": "https://images.unsplash.com/photo-1759392658577-4324fb89b991?crop=entropy&cs=srgb&fm=jpg&q=85",
      "description": "Abstract fluid shapes in green/blue (very soft)",
      "category": "section-accent/empty-state background"
    },
    {
      "url": "https://images.unsplash.com/photo-1636750308681-4630b6609993?crop=entropy&cs=srgb&fm=jpg&q=85",
      "description": "Painting-like blue/green/white swirls",
      "category": "reports cover ribbon or subtle header strip"
    },
    {
      "url": "https://images.pexels.com/photos/26885668/pexels-photo-26885668.jpeg",
      "description": "Soft teal-blue abstract",
      "category": "dashboard hero accent"
    }
  ],
  "component_path": {
    "card": "./components/ui/card.jsx",
    "button": "./components/ui/button.jsx",
    "badge": "./components/ui/badge.jsx",
    "select": "./components/ui/select.jsx",
    "separator": "./components/ui/separator.jsx",
    "table": "./components/ui/table.jsx",
    "popover": "./components/ui/popover.jsx",
    "calendar": "./components/ui/calendar.jsx",
    "alert": "./components/ui/alert.jsx",
    "toast": "./components/ui/sonner.jsx",
    "drawer": "./components/ui/drawer.jsx"
  },
  "extra_libraries": {
    "install": [
      "npm i framer-motion",
      "npm i date-fns"
    ],
    "notes": "Use framer-motion only for entrances and subtle hovers. shadcn Calendar already present; date-fns optional for formatting."
  },
  "implementation_rules": [
    "Files must be .js/.jsx (no .tsx)",
    "Only use components from ./components/ui for primitives (select, calendar, dropdown, toast, etc.)",
    "Never center-align the app container; maintain left-aligned reading flow",
    "Never use universal transition: all; target only the needed properties"
  ],
  "icons": {
    "library": "lucide-react",
    "examples_import": "import { Wallet, Percent, FileText, Calendar as CalendarIcon, RefreshCw, AlertTriangle, Inbox } from 'lucide-react';"
  },
  "states": {
    "payment_status_colors": {
      "paid": "text-[hsl(var(--success))]",
      "unpaid": "text-destructive",
      "partially_paid": "text-[hsl(var(--warning))]"
    },
    "badges": "Use outline badges for statuses to stay subtle on data-dense screens"
  },
  "buttons_selection": {
    "type": "Professional / Corporate",
    "variants": {
      "primary": "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:bg-[hsl(var(--primary))]/90 focus-visible:ring-2",
      "secondary": "bg-secondary text-secondary-foreground hover:bg-secondary/80",
      "outline": "border border-[hsl(var(--border))] hover:bg-accent",
      "ghost": "hover:bg-accent"
    },
    "sizes": {
      "sm": "h-8 px-3 text-sm",
      "md": "h-9 px-4",
      "lg": "h-10 px-5 text-base"
    }
  },
  "instructions_to_main_agent": [
    "1) Update /app/frontend/src/index.css :root with the semantic tokens listed in color_system.index_css_patch (keep formatting)",
    "2) Create FinanceSummaryCard.js using scaffold under components.finance_summary_card_in_booking_drawer and render it inside BookingDetailDrawer (place near other drawer cards)",
    "3) Build AgencyReportsPage.js with sections: header, ReportsFilterBar, KPIGrid, PaymentsBreakdownTable. Use data-testid attributes as specified",
    "4) Build HotelDashboardPage.js with period Select, Totals, AgencyStripChart (CSS width-based bars). Include data-testid=hotel-dashboard-period-select",
    "5) Ensure all interactive elements include data-testid per data_testids.required",
    "6) Integrate sonner toasts (./components/ui/sonner.jsx) for save-status success/error",
    "7) Respect gradient restriction rule; keep all cards solid surfaces; if any gradient area >20% viewport, fallback to solid",
    "8) Add framer-motion FadeIn wrapper to page sections only; avoid animating table body on updates",
    "9) Use Space Grotesk for numbers by applying font-['Space_Grotesk'] tabular-nums on monetary values"
  ]
}

<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts" 
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>