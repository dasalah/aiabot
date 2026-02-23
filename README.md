# 🤖 ربات تلگرام انجمن علمی هوش مصنوعی
## دانشگاه سیستان و بلوچستان

ربات رسمی انجمن علمی هوش مصنوعی برای مدیریت رویدادها، ثبت‌نام اعضا و اطلاع‌رسانی.

---

## 🗂️ ساختار پروژه

```
├── bot/                    # کد اصلی ربات تلگرام
│   ├── main.py             # نقطه ورود ربات
│   ├── config.py           # بارگذاری تنظیمات از YAML و env
│   ├── database.py         # مدیر پایگاه داده SQLite
│   ├── fsm.py              # ماشین حالت برای فرآیند ثبت‌نام
│   ├── handlers/           # هندلرهای رویدادهای تلگرام
│   ├── middlewares/        # میان‌افزارهای احراز هویت و عضویت
│   ├── utils/              # ابزارهای کمکی
│   └── api/                # REST API داخلی
├── web/                    # پنل مدیریت وب (Quart)
│   ├── app.py              # برنامه وب
│   ├── routes/             # مسیرهای وب
│   ├── templates/          # قالب‌های HTML
│   └── static/             # فایل‌های استاتیک
├── config/
│   ├── messages.yaml       # تمام متن‌های فارسی
│   ├── settings.yaml       # تنظیمات ربات
│   └── channels.yaml       # لیست کانال‌های اجباری
├── data/                   # ایجاد می‌شود در زمان اجرا
├── logs/                   # ایجاد می‌شود در زمان اجرا
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## ⚙️ پیش‌نیازها

### متغیرهای محیطی

فایل `.env.example` را کپی کنید:

```bash
cp .env.example .env
```

| متغیر | توضیح |
|---|---|
| `API_ID` | شناسه API از my.telegram.org |
| `API_HASH` | هش API از my.telegram.org |
| `BOT_TOKEN` | توکن ربات از @BotFather |
| `SUPERADMIN_IDS` | شناسه تلگرام سوپرادمین‌ها (با کاما جدا) |
| `WEB_SECRET_KEY` | کلید مخفی تصادفی برای پنل وب |
| `WEB_ADMIN_PASSWORD` | رمز ورود به پنل مدیریت |

---

## 🚀 راه‌اندازی روی VPS Debian

```bash
# نصب پیش‌نیازها
sudo apt update && sudo apt install -y python3.11 python3.11-venv git

# کلون و نصب
git clone https://github.com/dasalah/aiabot.git && cd aiabot
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# تنظیمات
cp .env.example .env && nano .env

# اجرا
python -m bot.main
# در ترمینال جداگانه:
python -m web.app
```

## 🐳 اجرا با Docker

```bash
cp .env.example .env
# ویرایش .env
docker compose up -d
```

## 🔒 نکات امنیتی

- فایل `.env` را هرگز در گیت کامیت نکنید
- از رمز عبور قوی برای `WEB_ADMIN_PASSWORD` استفاده کنید
- برای دسترسی عمومی از Nginx با SSL استفاده کنید

## 📋 ویژگی‌ها

- مدیریت رویدادها (ایجاد، ویرایش، حذف، آرشیو)
- ثبت‌نام با FSM با اعتبارسنجی کد ملی ایرانی
- بررسی عضویت در کانال‌های اجباری
- پرداخت آنلاین با آپلود رسید
- تأیید/رد ثبت‌نام توسط ادمین
- ارسال یادآوری خودکار
- پنل مدیریت وب با پشتیبانی RTL
- خروجی Excel از ثبت‌نام‌ها
- برادکست پیام به کاربران
- API داخلی REST برای وبسایت/مینی‌اپ

---

# 🤖 AI Association Telegram Bot — University of Sistan and Baluchestan

**Quick Setup:**
1. Copy `.env.example` → `.env` and fill credentials
2. Edit `config/*.yaml` as needed
3. Run: `docker compose up -d`
