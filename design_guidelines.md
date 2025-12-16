{
  "product_name": "Agentis Pro (Turizm Acenta Otomasyon + B2B Portal)",
  "brand_attributes": ["operasyonel", "güvenilir", "hızlı", "sakin ve berrak", "analitik"],
  "audience": [
    "Operasyon (rezervasyon, kontenjan, fiyat)",
    "Satış (teklif→rezervasyon)",
    "Finans (tahsilat, rapor)",
    "B2B Alt Acenteler (portal)",
    "Yönetici (rol/kurallar)"
  ],
  "information_architecture": {
    "role_based_nav": {
      "roles": ["admin", "operasyon", "satis", "finans", "b2b-agent"],
      "menu_groups": [
        {"label": "Genel", "items": ["Gösterge Paneli", "Takvim", "Rezervasyonlar"]},
        {"label": "Ürünler", "items": ["Turlar", "Oteller", "Villalar", "Transferler", "Fiyat & Aksiyon"]},
        {"label": "CRM", "items": ["Müşteriler", "Lead'ler", "Teklifler"]},
        {"label": "Finans", "items": ["Tahsilatlar", "Faturalar", "Raporlar"]},
        {"label": "Ayarlar", "items": ["Kullanıcılar & Roller", "Kota/Komisyon", "Şablonlar (voucher, teklif)"]},
        {"label": "B2B Portal", "items": ["Giriş", "Rezervasyon Oluştur", "Fiyat Kartları"]}
      ],
      "visibility_rule": "Menü öğeleri kullanıcı rolüne göre filtrelenir; erişimi olmayan sayfalarda nav öğesi görüntülenmez."
    }
  },
  "typography": {
    "pairing": {
      "headings": "Manrope",
      "body": "Inter",
      "mono": "Roboto Mono"
    },
    "cdn": [
      "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
      "https://fonts.googleapis.com/css2?family=Manrope:wght@600;700;800&display=swap"
    ],
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "body": "text-sm md:text-base",
      "small": "text-xs"
    },
    "weights": {"h": 700, "body": 500},
    "tracking": {"tight": "tracking-[-0.01em]", "wide": "tracking-wide"}
  },
  "color_system": {
    "light": {
      "background": "hsl(210 20% 99%)",
      "foreground": "hsl(220 24% 14%)",
      "surface": "hsl(0 0% 100%)",
      "muted": "hsl(210 16% 96%)",
      "primary": "hsl(185 60% 35%)", 
      "primary-foreground": "hsl(0 0% 100%)",
      "accent": "hsl(200 70% 42%)",
      "accent-foreground": "hsl(0 0% 100%)",
      "secondary": "hsl(40 80% 88%)", 
      "secondary-foreground": "hsl(24 30% 22%)",
      "success": "hsl(151 55% 32%)",
      "warning": "hsl(35 92% 45%)",
      "danger": "hsl(8 76% 46%)",
      "border": "hsl(210 16% 86%)",
      "ring": "hsl(185 60% 35%)"
    },
    "dark": {
      "background": "hsl(216 33% 8%)",
      "foreground": "hsl(210 20% 98%)",
      "surface": "hsl(222 47% 11%)",
      "muted": "hsl(220 15% 15%)",
      "primary": "hsl(185 65% 45%)",
      "primary-foreground": "hsl(210 20% 8%)",
      "accent": "hsl(200 75% 50%)",
      "accent-foreground": "hsl(210 20% 8%)",
      "secondary": "hsl(40 60% 20%)",
      "secondary-foreground": "hsl(40 85% 92%)",
      "success": "hsl(151 55% 38%)",
      "warning": "hsl(35 92% 55%)",
      "danger": "hsl(8 76% 54%)",
      "border": "hsl(220 13% 18%)",
      "ring": "hsl(185 65% 45%)"
    },
    "states": {
      "booking": {
        "confirmed": "hsl(151 55% 32%)",
        "option": "hsl(200 70% 42%)",
        "waitlist": "hsl(35 92% 45%)",
        "cancelled": "hsl(8 76% 46%)",
        "blocked": "hsl(220 14% 62%)"
      }
    },
    "gradient_policy": {
      "allowed": "Yumuşak 2-3 renkli gradientler SADECE bölüm arkaplanları için. Küçük UI elemanlarında gradient yasak.",
      "palette_examples": [
        "linear-gradient(135deg, hsl(185 70% 96%), hsl(200 80% 96%), hsl(40 90% 96%))",
        "linear-gradient(180deg, hsl(200 65% 97%), hsl(185 60% 97%))"
      ],
      "prohibited": ["koyu/doygun mor-pembe, mavi-mor, kırmızı-pembe, yeşil-mavi koyu geçişler"],
      "max_coverage": "Viewport'un %20'sinden fazla alan kaplamayacak"
    }
  },
  "design_tokens": {
    "css_vars_to_add_in_index.css": {
      ":root": {
        "--brand-ocean": "185 60% 35%",
        "--brand-aegean": "200 70% 42%",
        "--brand-sand": "40 80% 88%",
        "--brand-olive": "96 20% 32%",
        "--success": "151 55% 32%",
        "--warning": "35 92% 45%",
        "--danger": "8 76% 46%",
        "--radius-lg": "0.8rem",
        "--radius-md": "0.6rem",
        "--radius-sm": "0.4rem",
        "--shadow-sm": "0 1px 2px rgba(0,0,0,0.06)",
        "--shadow-md": "0 8px 24px rgba(3, 7, 18, 0.08)",
        "--shadow-lg": "0 20px 40px rgba(3,7,18,0.12)"
      }
    },
    "spacing_rules": "Temel aralık 8px. Admin için ferah: 24px section padding, tablolarda 14px hücre padding.",
    "focus": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2"
  },
  "layout": {
    "desktop_first_grid": "App shell: sol kalın sidebar (w-72), üstte topbar (56px), içerik alanı container mx-auto max-w-[1400px] px-6.",
    "mobile": "Alt tab bar (optional) ve hamburger ile açılan Drawer sidebar.",
    "containers": {
      "card": "bg-white dark:bg-[hsl(var(--card))] rounded-xl shadow-sm border",
      "section": "py-8 md:py-10"
    },
    "grid_examples": {
      "dashboard_kpis": "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5",
      "two_column": "grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6"
    }
  },
  "navigation": {
    "sidebar": {
      "pattern": "Resizable + ScrollArea içinde dikey menü; aktif öğe sol kenarda 2px accent şerit.",
      "item_classes": "flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium",
      "active_classes": "bg-muted text-foreground border-l-2 border-[hsl(var(--ring))]"
    },
    "topbar": {
      "elements": ["global arama", "tarih seçici", "hızlı aksiyonlar", "kullanıcı menüsü"],
      "classes": "h-14 border-b bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/75"
    }
  },
  "components": {
    "filters_bar": {
      "description": "Yoğun tablo/kalendara üstten filtre. Popover + Command palette ile çoklu seçici.",
      "uses": ["Popover", "Command", "Badge", "Button", "Calendar"],
      "tailwind": "flex flex-wrap items-center gap-2",
      "snippet_lines": [
        "import { Popover, PopoverTrigger, PopoverContent } from './components/ui/popover';",
        "import { Command, CommandInput, CommandList } from './components/ui/command';",
        "<div className=\"flex flex-wrap items-center gap-2\">",
        "  <Popover>",
        "    <PopoverTrigger asChild>",
        "      <button data-testid=\"filter-product-button\" className=\"btn-ghost px-3 py-2 rounded-md border\">Ürün</button>",
        "    </PopoverTrigger>",
        "    <PopoverContent className=\"p-0 w-72\">",
        "      <Command>",
        "        <CommandInput placeholder=\"Tür ara\" />",
        "        <CommandList>...</CommandList>",
        "      </Command>",
        "    </PopoverContent>",
        "  </Popover>",
        "  <Calendar mode=\"range\" onSelect={setDate} data-testid=\"filter-date-range\" />",
        "</div>"
      ]
    },
    "data_table": {
      "description": "Sık kullanılan yoğun tablo. Sticky header, satır üzerinde hızlı aksiyon menüsü.",
      "uses": ["Table", "Checkbox", "DropdownMenu", "Tooltip", "ScrollArea", "Badge"],
      "patterns": ["satır seçimi", "çoklu sil/işlem", "kolon görünürlüğü"],
      "tailwind": "border rounded-lg overflow-hidden",
      "row_states": {
        "danger": "bg-red-50",
        "warning": "bg-amber-50",
        "muted": "bg-muted"
      },
      "snippet_lines": [
        "import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from './components/ui/table';",
        "import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from './components/ui/dropdown-menu';",
        "<div className=\"border rounded-lg overflow-auto max-h-[70vh]\" data-testid=\"reservations-table\">",
        " <Table>",
        "  <TableHeader className=\"sticky top-0 bg-white z-10\"> ... </TableHeader>",
        "  <TableBody> ... satırlar ... </TableBody>",
        " </Table>",
        "</div>"
      ]
    },
    "inventory_calendar": {
      "description": "Kontenjan & müsaitlik için grid. Satırlar ürün/oda/araç, sütunlar tarih.",
      "uses": ["Calendar", "ScrollArea", "Tooltip", "Sheet", "Badge"],
      "states_color": {
        "available": "bg-emerald-50 text-emerald-700",
        "low": "bg-amber-50 text-amber-700",
        "full": "bg-red-50 text-red-700",
        "blocked": "bg-zinc-100 text-zinc-600"
      },
      "tailwind": "grid auto-rows-[40px] border rounded-lg",
      "snippet_lines": [
        "<div className=\"grid [grid-template-columns:220px_repeat(14,1fr)] border rounded-lg\" data-testid=\"inventory-grid\">",
        "  <div className=\"sticky left-0 z-10 bg-white border-r\">Oda/Ürün</div>",
        "  {/* 14 gün sütun başlıkları */}",
        "  {[...Array(14)].map((_,i)=> <div key={i} className=\"text-center text-xs py-2 border-l\">{format(addDays(start,i),'dd MMM')}</div>)}",
        "  {/* satırlar */}",
        "</div>"
      ]
    },
    "reservation_drawer": {
      "description": "Sağdan açılan detay çekmecesi. Durum, fiyat, komisyon ve aksiyonlar.",
      "uses": ["Sheet", "Separator", "Tabs", "Badge", "Button", "Textarea"],
      "tailwind": "",
      "snippet_lines": [
        "import { Sheet, SheetContent, SheetHeader, SheetTitle } from './components/ui/sheet';",
        "<Sheet open={open} onOpenChange={setOpen}>",
        "  <SheetContent side=\"right\" className=\"w-[520px] max-w-full\" data-testid=\"reservation-detail-drawer\">",
        "    <SheetHeader>",
        "      <SheetTitle>Rezervasyon #AG-2342</SheetTitle>",
        "    </SheetHeader>",
        "    <div className=\"space-y-4\">...</div>",
        "  </SheetContent>",
        "</Sheet>"
      ]
    },
    "offer_to_booking": {
      "description": "Teklif kartları → seç → müşteri bilgisi → ödeme/tahsilat → voucher.",
      "uses": ["Card", "Tabs", "Button", "Input", "Select", "Stepper (custom)"],
      "tailwind": "grid grid-cols-1 lg:grid-cols-3 gap-5"
    },
    "b2b_portal": {
      "description": "Basit ve hızlı B2B rezervasyon akışı. Partner rate/komisyon otomatik uygulanır.",
      "uses": ["Card", "Select", "Calendar", "Input", "Button", "Badge"],
      "labels_tr": {"login": "B2B Giriş", "new_booking": "Yeni Rezervasyon"}
    },
    "voucher_print": {
      "description": "Baskı dostu şablon. Logo, müşteri, ürün, tarih, QR ve iptal şartları.",
      "print_css_lines": [
        "@media print {",
        "  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }",
        "  .no-print { display: none !important }",
        "  .voucher { box-shadow: none; border: none; }",
        "}"
      ]
    },
    "toasts": {
      "library": "sonner",
      "path": "./components/ui/sonner.jsx",
      "usage_lines": [
        "import { toast } from './components/ui/sonner';",
        "toast.success('Kaydedildi', { description: 'Rezervasyon güncellendi' });"
      ]
    },
    "forms": {
      "principles": ["Her input için label ve yardım metni", "Zorunlu alan *", "Hata altında gösterilir"],
      "uses": ["Form", "Input", "Select", "Textarea", "RadioGroup", "Switch"],
      "validation": "Alan hatalarında aria-invalid ve role=alert kullan.",
      "testid_rule": "Tüm form alanları data-testid içerir: data-testid=\"customer-phone-input\" gibi"
    }
  },
  "pages": {
    "dashboard": {
      "sections": ["KPI Kartları", "Bugünün İşleri", "Mini Takvim", "Son Rezervasyonlar", "Gelir Grafiği"],
      "charts": "Recharts AreaChart + BarChart",
      "quick_actions": ["Yeni Teklif", "Rezervasyon Ekle", "Voucher Yazdır"],
      "kpi_card_classes": "rounded-xl border bg-white p-5 shadow-sm"
    },
    "urun_yonetimi": {
      "tabs": ["Tur", "Otel", "Villa", "Transfer"],
      "table_columns": ["Ad", "Tedarikçi", "Kategori", "Durum", "Fiyat", "Aksiyon"],
      "actions": ["Düzenle", "Fiyat/Aksiyon", "Müsaitlik"]
    },
    "fiyat_aksiyon": {"view": "tablo + sağ panel", "notes": "Sezon, özel tarih, erken rezervasyon, kupon"},
    "kontenjan_takvimi": {"view": "inventory_calendar", "legend": ["Müsait", "Az", "Dolu", "Bloke"]},
    "rezervasyon_yonetimi": {"view": "tablo + reservation_drawer", "quick_filters": ["Bugün", "Bu Hafta", "Bekleyen Ödeme", "İptal"]},
    "crm": {"entities": ["Müşteri", "Lead", "Şirket"], "timeline": true, "quick_actions": ["Teklif", "Rezervasyon", "Mesaj"]},
    "b2b_portal": {"views": ["Login", "Yeni Rezervasyon", "Fiyat Kartları"], "export": ["voucher", "proforma"]},
    "raporlar": {"charts": ["Gelir", "Doluluk", "Partner Performans"], "export": ["CSV", "XLSX"]},
    "kullanici_roller": {"rbac": true, "permissions_matrix": true}
  },
  "buttons": {
    "style": "Professional / Corporate",
    "radius": "var(--radius-md)",
    "variants": {
      "primary": "bg-[hsl(var(--brand-ocean))] text-white hover:bg-teal-700 focus-visible:ring-teal-600",
      "secondary": "bg-[hsl(var(--brand-sand))] text-slate-900 hover:bg-amber-100",
      "ghost": "bg-transparent text-foreground hover:bg-muted border"
    },
    "sizes": {"sm": "h-9 px-3", "md": "h-10 px-4", "lg": "h-11 px-5"},
    "motion": "hover:shadow-md active:scale-[0.99] transition-[background-color,box-shadow] duration-200 ease-out"
  },
  "icons": {"library": "lucide-react", "note": "Asla emoji kullanma. lucide-react CDN/ paket kullan."},
  "motion_microinteractions": {
    "principles": [
      "Asla universal transition: all kullanma",
      "Görsel hiyerarşi: kart girişleri 140ms fade+translate",
      "Hoverlarda yalnızca renk/arka plan/box-shadow transition"
    ],
    "suggested": ["Framer Motion ile sayfa geçişlerinde yumuşak fade", "Scroll ile section başlıklarında 6px parallax"]
  },
  "accessibility": {
    "contrast": "WCAG AA yakala (metin/zemin). Koyu metin + açık zemin tercih.",
    "focus": "Görünür focus ring. Tab ile tüm etkileşimler ulaşılabilir.",
    "reduced_motion": "prefers-reduced-motion: motion-disable.",
    "aria": "İkon butonlarda aria-label zorunlu",
    "language": "Türkçe UI etiketleri; tarih/sayı yerelleştirme (TR)"
  },
  "testing": {
    "policy": "Tüm etkileşimli/ kritik bilgi elemanlarında data-testid zorunlu.",
    "naming": "kebab-case ve rol bazlı: reservation-row-actions, login-form-submit-button",
    "examples": [
      "<button data-testid=\"new-offer-button\">Yeni Teklif</button>",
      "<input data-testid=\"customer-phone-input\" />",
      "<div data-testid=\"user-balance-text\">12.450,00 TL</div>"
    ]
  },
  "libraries": {
    "install": [
      "npm i recharts framer-motion lucide-react d3 d3-scale",
      "npm i i18next react-i18next dayjs"
    ],
    "usage_notes": {
      "recharts": "KPI ve rapor grafiklerinde. ResponsiveContainer zorunlu.",
      "framer_motion": "Sayfa geçişleri ve kart giriş animasyonları.",
      "d3": "Yoğunluk/ısı haritası lejandı ve renk skaları için opsiyonel.",
      "i18n": "TR ana dil; en fallback."
    }
  },
  "css_utilities": {
    "noise_overlay": ".noise-overlay{position:absolute;inset:0;pointer-events:none;background-image:url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"140\" height=\"140\"><filter id=\"n\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.8\" numOctaves=\"4\"/></filter><rect width=\"100%\" height=\"100%\" filter=\"url(%23n)\" opacity=\"0.025\"/></svg>');}",
    "elevation_classes": {
      "card": "shadow-sm",
      "panel": "shadow-md",
      "popover": "shadow-lg"
    }
  },
  "image_urls": [
    {
      "category": "dashboard-hero",
      "description": "Ege kıyısı aerial – hafif blur ile topbar arkaplanı olarak",
      "url": "https://images.pexels.com/photos/8633905/pexels-photo-8633905.jpeg"
    },
    {
      "category": "empty-states",
      "description": "Sahil kasabası drone – boş CRM/teklif listesi illüstrasyonu",
      "url": "https://images.pexels.com/photos/27821555/pexels-photo-27821555.jpeg"
    }
  ],
  "component_path": {
    "button": "./components/ui/button.jsx",
    "table": "./components/ui/table.jsx",
    "calendar": "./components/ui/calendar.jsx",
    "sheet": "./components/ui/sheet.jsx",
    "drawer": "./components/ui/drawer.jsx",
    "popover": "./components/ui/popover.jsx",
    "command": "./components/ui/command.jsx",
    "select": "./components/ui/select.jsx",
    "badge": "./components/ui/badge.jsx",
    "tabs": "./components/ui/tabs.jsx",
    "dialog": "./components/ui/dialog.jsx",
    "toast": "./components/ui/toaster.jsx",
    "sonner": "./components/ui/sonner.jsx",
    "input": "./components/ui/input.jsx",
    "checkbox": "./components/ui/checkbox.jsx",
    "switch": "./components/ui/switch.jsx",
    "scrollarea": "./components/ui/scroll-area.jsx",
    "menubar": "./components/ui/menubar.jsx",
    "navigation_menu": "./components/ui/navigation-menu.jsx",
    "tooltip": "./components/ui/tooltip.jsx",
    "separator": "./components/ui/separator.jsx",
    "card": "./components/ui/card.jsx"
  },
  "example_scaffolds": {
    "app_shell_lines": [
      "import { ScrollArea } from './components/ui/scroll-area';",
      "import { Separator } from './components/ui/separator';",
      "export default function Shell(){",
      " return (",
      "  <div className=\"grid min-h-screen [grid-template-columns:18rem_1fr]\">",
      "    <aside className=\"border-r bg-white hidden md:block\"> ... sidebar ... </aside>",
      "    <div className=\"flex flex-col\">",
      "      <header className=\"h-14 border-b bg-white/90 backdrop-blur\"> ... topbar ... </header>",
      "      <main className=\"flex-1 p-6\"> ... content ... </main>",
      "    </div>",
      "  </div>",
      " )",
      "}"
    ],
    "kpi_card_lines": [
      "<div className=\"rounded-xl border bg-white p-5 shadow-sm\" data-testid=\"kpi-card-bookings-today\">",
      "  <div className=\"text-sm text-slate-500\">Bugünkü Rezervasyon</div>",
      "  <div className=\"text-3xl font-bold\">128</div>",
      "</div>"
    ],
    "row_actions_lines": [
      "import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from './components/ui/dropdown-menu';",
      "<DropdownMenu>",
      "  <DropdownMenuTrigger asChild>",
      "    <button className=\"icon-button\" aria-label=\"Satır işlemleri\" data-testid=\"reservation-row-actions\">•••</button>",
      "  </DropdownMenuTrigger>",
      "  <DropdownMenuContent align=\"end\">",
      "    <DropdownMenuItem>Düzenle</DropdownMenuItem>",
      "    <DropdownMenuItem>Voucher Yazdır</DropdownMenuItem>",
      "  </DropdownMenuContent>",
      "</DropdownMenu>"
    ]
  },
  "data_visualization": {
    "chart_palette": ["#0E7490", "#0284C7", "#22C55E", "#F59E0B", "#EF4444"],
    "empty_states": "Basit illüstrasyon + net CTA: 'Yeni Teklif Oluştur'",
    "legend": "D3 scaleSequential ile sıcaklık efsanesi (opsiyonel)"
  },
  "i18n_texts_tr": {
    "common": {
      "search": "Ara...",
      "save": "Kaydet",
      "cancel": "İptal",
      "create": "Oluştur",
      "edit": "Düzenle",
      "delete": "Sil"
    },
    "booking_states": {"confirmed": "Onaylandı", "option": "Opsiyon", "waitlist": "Bekleme", "cancelled": "İptal", "blocked": "Bloke"}
  },
  "instructions_to_main_agent": "1) Önce app shell ve rol bazlı sidebar'ı kur. 2) Dashboard KPI kartları ve Recharts'ı ekle. 3) Rezervasyon tablosu + detay çekmecesi (Sheet) uygula. 4) Kontenjan takvimi gridini oluştur ve Calendar ile tarih aralığı filtresi bağla. 5) B2B login + hızlı rezervasyon akışını Card formu ile hazırla. 6) Tüm buton, link ve kritik metinlerde data-testid ata. 7) Gradientleri sadece bölüm arkaplanında, maksimum %20 alan kuralına uyarak kullan. 8) Tüm dropdown, calendar, toast vb. için shadcn/ui kullan. 9) .js/.jsx dosya yapısına sadık kal.",
  "general_ui_ux_design_guidelines": "- You must not apply universal transition. Eg: transition: all. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n- You must not center align the app container, ie do not add .App { text-align: center; } in the css file. This disrupts the human natural reading flow of text\n- NEVER: use AI assistant Emoji characters like🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use FontAwesome cdn or lucid-react library already installed in the package.json\n\n GRADIENT RESTRICTION RULE\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\nENFORCEMENT RULE:\n    • Id gradient area exceeds 20% of viewport OR affects readability, THEN use solid colors\n\nHow and where to use:\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, do not use purple color. Use color like light green, ocean blue, peach orange etc\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\nComponent Reuse:\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\nIMPORTANT: Do not use HTML based component like dropdown, calendar, toast etc. You MUST always use /app/frontend/src/components/ui/ only as a primary components as these are modern and stylish component\n\nBest Practices:\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\nExport Conventions:\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\nToasts:\n  - Use sonner for toasts\"\n  - Sonner component are located in /app/src/components/ui/sonner.tsx\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals."
}
