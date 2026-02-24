/**
 * Shared Zod validation schemas for all forms.
 * Used with react-hook-form + @hookform/resolvers/zod.
 */
import { z } from "zod";

// ─── Ortak Mesajlar ───────────────────────────────────
const msg = {
  required: "Bu alan zorunludur",
  email: "Geçerli bir e-posta adresi girin",
  minPassword: "Şifre en az 6 karakter olmalıdır",
  maxPassword: "Şifre en fazla 128 karakter olabilir",
  minName: "İsim en az 2 karakter olmalıdır",
  maxName: "İsim en fazla 100 karakter olabilir",
  phone: "Geçerli bir telefon numarası girin",
  positiveNumber: "Pozitif bir sayı girin",
  url: "Geçerli bir URL girin",
  minRoles: "En az bir rol seçilmelidir",
};

// ─── Auth Schemas ─────────────────────────────────────
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, msg.required)
    .email(msg.email),
  password: z
    .string()
    .min(1, msg.required)
    .min(6, msg.minPassword)
    .max(128, msg.maxPassword),
});

export const registerSchema = z.object({
  email: z.string().min(1, msg.required).email(msg.email),
  name: z.string().min(2, msg.minName).max(100, msg.maxName),
  password: z.string().min(6, msg.minPassword).max(128, msg.maxPassword),
});

export const passwordResetSchema = z.object({
  email: z.string().min(1, msg.required).email(msg.email),
});

export const newPasswordSchema = z
  .object({
    password: z.string().min(6, msg.minPassword).max(128, msg.maxPassword),
    confirmPassword: z.string().min(1, msg.required),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Şifreler eşleşmiyor",
    path: ["confirmPassword"],
  });

// ─── User Management Schemas ──────────────────────────
export const createUserSchema = z.object({
  email: z.string().min(1, msg.required).email(msg.email),
  name: z.string().min(2, msg.minName).max(100, msg.maxName),
  password: z.string().min(6, msg.minPassword).max(128, msg.maxPassword),
  roles: z.array(z.string()).min(1, msg.minRoles),
});

// ─── Booking / Guest Schemas ──────────────────────────
export const guestSchema = z.object({
  first_name: z.string().min(1, "Misafir adı zorunludur").max(100, msg.maxName),
  last_name: z.string().min(1, "Misafir soyadı zorunludur").max(100, msg.maxName),
  email: z.string().email(msg.email).optional().or(z.literal("")),
  phone: z.string().optional(),
  nationality: z.string().optional(),
});

export const bookingSchema = z.object({
  check_in: z.string().min(1, "Giriş tarihi zorunludur"),
  check_out: z.string().min(1, "Çıkış tarihi zorunludur"),
  adults: z.coerce.number().int().min(1, "En az 1 yetişkin gerekli"),
  children: z.coerce.number().int().min(0).default(0),
  guests: z.array(guestSchema).min(1, "En az 1 misafir bilgisi giriniz"),
  notes: z.string().optional(),
});

// ─── Contact / Partner Apply Schemas ──────────────────
export const contactSchema = z.object({
  name: z.string().min(2, msg.minName).max(100, msg.maxName),
  email: z.string().min(1, msg.required).email(msg.email),
  phone: z.string().optional(),
  message: z.string().min(10, "Mesaj en az 10 karakter olmalıdır").max(2000),
});

export const partnerApplySchema = z.object({
  company_name: z.string().min(2, "Firma adı zorunludur").max(200),
  contact_name: z.string().min(2, msg.minName).max(100, msg.maxName),
  email: z.string().min(1, msg.required).email(msg.email),
  phone: z.string().min(1, msg.required),
  city: z.string().optional(),
  message: z.string().optional(),
});

// ─── Product / Pricing Schemas ────────────────────────
export const productSchema = z.object({
  title: z.string().min(2, "Ürün adı zorunludur").max(300),
  description: z.string().optional(),
  price: z.coerce.number().positive(msg.positiveNumber),
  currency: z.string().min(1, "Para birimi zorunludur"),
  status: z.enum(["active", "draft", "archived"]).default("draft"),
});

// ─── CRM Schemas ──────────────────────────────────────
export const customerSchema = z.object({
  name: z.string().min(2, msg.minName).max(200),
  email: z.string().email(msg.email).optional().or(z.literal("")),
  phone: z.string().optional(),
  company: z.string().optional(),
  notes: z.string().optional(),
});

export const dealSchema = z.object({
  title: z.string().min(2, "Fırsat adı zorunludur").max(300),
  value: z.coerce.number().min(0).default(0),
  currency: z.string().default("TRY"),
  stage: z.string().min(1, "Aşama seçiniz"),
  contact_name: z.string().optional(),
  notes: z.string().optional(),
});

// ─── Settings Schemas ─────────────────────────────────
export const profileSchema = z.object({
  name: z.string().min(2, msg.minName).max(100, msg.maxName),
  email: z.string().email(msg.email),
  phone: z.string().optional(),
});

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Mevcut şifre zorunludur"),
    new_password: z.string().min(6, msg.minPassword).max(128, msg.maxPassword),
    confirm_password: z.string().min(1, msg.required),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Şifreler eşleşmiyor",
    path: ["confirm_password"],
  });
