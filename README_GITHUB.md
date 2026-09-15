# راه‌اندازی رایگان روی GitHub Actions — بدون کارت بانکی، بدون تحریم 🎉

گیت‌هاب مجوز رسمی سرویس به کاربرای ایران داره. به جای VPS، خود گیت‌هاب ۵ بار در روز یه کامپیوتر لینوکسی رایگان روشن می‌کنه، ویدیو می‌سازه و آپلود می‌کنه. هزینه: **صفر**.

## قدم ۱ — اکانت گیت‌هاب
- برو `github.com` → Sign up (ایمیل کافیه، کارت نمی‌خواد)

## قدم ۲ — ساخت ریپو
- New repository → اسم مثلاً `chessbot` → بذار **Public** باشه (پابلیک = دقیقه‌های Actions نامحدود و رایگان)
- ⚠️ چون Public می‌سازیم، **هیچ‌وقت فایل‌های لاگین رو داخل ریپو نذار!** (قدم ۳ اینو حل می‌کنه)

## قدم ۳ — آپلود پروژه (بدون فایل‌های لاگین)
قبل از آپلود این ۳ فایل رو از پوشه حذف/نگه‌دار کنار:
`token.pickle` ، `client_secrets.json` ، `state.json` و پوشه‌ی `out/`

آپلود با مرورگر راحت‌ترین راهه: توی صفحه ریپو → Add file → Upload files → همه‌ی فایل‌های chessyt (به‌همراه پوشه `.github` و `assets`) رو بکش بریز → Commit.
(یا با git: `git init` → `git add .` → commit → push)

## قدم ۴ — ذخیره‌ی لاگین یوتیوب به‌صورت Secret
توی PowerShell (ویندوز) داخل پوشه chessyt:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("token.pickle")) | Set-Clipboard   # کپی شد
```
حالا توی ریپو: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `TOKEN_PICKLE_B64` → Value: Ctrl+V
و برای client_secrets:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("client_secrets.json")) | Set-Clipboard
```
- Name: `CLIENT_SECRETS_B64` → Value: Ctrl+V

## قدم ۵ — تست و اجرا
- توی ریپو: تب **Actions** → گزینه‌ی اگه غیرفعاله، روی «Enable workflows» بزن
- «ChessPuzzleBot» → **Run workflow** → Run → اولین ویدیو همون‌جا ساخته و آپلود می‌شه ✅
- بعدش خودکار روزی ۵ بار (ساعت ۹/۱۲/۱۵/۱۸/۲۱ به وقت تهران) اجرا می‌شه

## نکته‌ها
- ⏰ کرن گیت‌هاب گاهی چند دقیقه تأخیر داره — طبیعیه.
- 🔁 ضد تکرار: ربات اول تاریخ آپلودهای یوتیوب رو چک می‌کنه پس پازل تکراری نمی‌ره.
- 🚫 کانال نو؟ اول با ۱ بار در روز شروع کن (کرون‌های اضافه رو توی `chessbot.yml` با # کامنت کن).
- 📄 لاگ هر اجرا توی تب Actions قابل مشاهده‌ست.
