import asyncio
import json
import os
import re
from datetime import datetime, date
from pathlib import Path
from playwright.async_api import async_playwright

MONTH_MAP_FR = {
    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
    'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
}
MONTH_MAP_EN = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}


def parse_amazon_date(date_str: str):
    if not date_str:
        return None
    s = date_str.strip().lower()
    s = re.sub(r'^(le|on)\s+', '', s)

    for month_name, month_num in MONTH_MAP_FR.items():
        if month_name in s:
            parts = s.replace(month_name, '').split()
            nums = [p for p in parts if re.match(r'^\d+$', p)]
            if len(nums) >= 2:
                try:
                    return date(int(nums[-1]), month_num, int(nums[0]))
                except ValueError:
                    pass

    for month_name, month_num in MONTH_MAP_EN.items():
        if month_name in s:
            parts = s.replace(month_name, '').split()
            nums = [p for p in parts if re.match(r'^\d+$', p)]
            if len(nums) >= 2:
                try:
                    return date(int(nums[-1]), month_num, int(nums[0]))
                except ValueError:
                    pass

    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    return None


class AmazonScraper:
    def __init__(self):
        self._otp_event = asyncio.Event()
        self._otp_code = None

    def set_otp(self, code: str):
        self._otp_code = code
        self._otp_event.set()

    async def run(self, email: str, password: str, marketplace: str,
                  start_date: str, end_date: str, ws):

        async def send(data: dict):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage',
                      '--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                viewport={'width': 1280, 'height': 900},
                locale='fr-FR',
            )

            # Hide webdriver flag + disable passkey/WebAuthn so Amazon skips that dialog
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                if (window.PublicKeyCredential) {
                    window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable =
                        () => Promise.resolve(false);
                    window.PublicKeyCredential.isConditionalMediationAvailable =
                        () => Promise.resolve(false);
                }
                if (navigator.credentials && navigator.credentials.get) {
                    const _origGet = navigator.credentials.get.bind(navigator.credentials);
                    navigator.credentials.get = (opts) => {
                        if (opts && opts.publicKey) return Promise.reject(new Error('disabled'));
                        return _origGet(opts);
                    };
                }
            """)

            page = await context.new_page()

            try:
                # ── Login ──
                await send({"type": "status", "message": "Connexion à Amazon..."})
                login_result = await self._login(page, email, password, marketplace, send)

                if login_result == 'otp_required':
                    await send({"type": "otp_required"})
                    self._otp_event.clear()
                    await asyncio.wait_for(self._otp_event.wait(), timeout=300)
                    await self._submit_otp(page, self._otp_code)
                    await asyncio.sleep(3)

                elif login_result == 'captcha_required':
                    await send({"type": "captcha_required",
                                "message": "CAPTCHA détecté. Résolvez-le dans la fenêtre du navigateur puis attendez."})
                    await asyncio.sleep(30)

                elif login_result == 'error':
                    await send({"type": "error", "message": "Échec de la connexion. Vérifiez vos identifiants."})
                    return

                current_url = page.url
                if 'signin' in current_url or 'ap/signin' in current_url:
                    await send({"type": "error",
                                "message": "La connexion a échoué. Vérifiez email/mot de passe."})
                    return

                await send({"type": "status", "message": "Connecté ! Recherche des commandes..."})

                # ── Fetch orders ──
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

                all_orders = []
                for year in range(start_dt.year, end_dt.year + 1):
                    await send({"type": "status",
                                "message": f"Analyse des commandes {year}..."})
                    orders = await self._get_year_orders(
                        page, marketplace, year, start_dt, end_dt, send)
                    all_orders.extend(orders)
                    await send({"type": "orders_found",
                                "count": len(all_orders), "year": year})

                if not all_orders:
                    await send({"type": "completed", "count": 0, "orders": []})
                    return

                await send({
                    "type": "completed",
                    "count": len(all_orders),
                    "orders": all_orders,
                })

            except Exception as exc:
                await send({"type": "error", "message": f"Erreur inattendue : {exc}"})
            finally:
                await browser.close()

    # ────────────────────────────────────────────────────────────────────────
    async def _dismiss_passkey(self, page, marketplace: str):
        """Click 'Fermer/Close' if Amazon shows a passkey dialog, then make sure
        we're on the standard email/password signin page."""
        try:
            # Look for the Fermer / Close button in the passkey modal
            for selector in [
                'button:has-text("Fermer")',
                'button:has-text("Close")',
                'button:has-text("Annuler")',
                '[data-testid="passkey-dismiss-button"]',
            ]:
                btn = page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    await asyncio.sleep(1.5)
                    break

            # If the page redirected to a passkey-specific URL (e.g. /ap/signin/XXX),
            # navigate back to the standard email form.
            if re.search(r'/ap/signin/\d', page.url):
                std_url = f"https://www.{marketplace}/ap/signin?openid.mode=checkid_setup&openid.ns=http://specs.openid.net/auth/2.0&openid.claimed_id=http://specs.openid.net/auth/2.0/identifier_select&openid.identity=http://specs.openid.net/auth/2.0/identifier_select&openid.assoc_handle=frflex&openid.return_to=https://www.{marketplace}/"
                await page.goto(std_url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(1.5)

        except Exception:
            pass  # Non-blocking — proceed anyway

    async def _login(self, page, email, password, marketplace, send):
        url = (f"https://www.{marketplace}/ap/signin"
               "?openid.return_to=https%3A%2F%2Fwww." + marketplace + "%2F"
               "&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
               "&openid.assoc_handle=frflex&openid.mode=checkid_setup"
               "&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
               "&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0")

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)

        # Dismiss passkey dialog if Amazon shows one before the email form
        await self._dismiss_passkey(page, marketplace)

        try:
            email_field = page.locator('#ap_email')
            await email_field.wait_for(timeout=10000)
            await email_field.fill(email)
            await asyncio.sleep(0.5)

            # Amazon has two elements with id="continue" (a <span> and an <input>)
            # → target the actual submit input to avoid strict-mode violation
            await page.locator('input#continue').click()
            await asyncio.sleep(2)

            password_field = page.locator('#ap_password')
            await password_field.wait_for(timeout=10000)
            await password_field.fill(password)
            await asyncio.sleep(0.5)

            # Same issue possible on signInSubmit — use input selector
            await page.locator('input#signInSubmit').click()
            await asyncio.sleep(3)

        except Exception as exc:
            await send({"type": "warning", "message": f"Problème lors de la saisie : {exc}"})
            return 'error'

        if await page.locator('#auth-mfa-otpcode').count() > 0:
            return 'otp_required'
        if await page.locator('#auth-captcha-image-wrapper').count() > 0:
            return 'captcha_required'
        if 'signin' in page.url or 'ap/signin' in page.url:
            return 'error'

        return 'success'

    async def _submit_otp(self, page, code: str):
        otp_field = page.locator('#auth-mfa-otpcode')
        await otp_field.fill(code)
        submit = page.locator('input#auth-signin-button')
        if await submit.count() > 0:
            await submit.click()
        else:
            await page.keyboard.press('Enter')
        await asyncio.sleep(3)

    async def _get_year_orders(self, page, marketplace, year,
                                start_date, end_date, send):
        """Extract orders by scanning raw HTML for order-ID patterns.
        This avoids relying on Amazon's frequently-changing CSS classes."""
        orders = []
        seen_ids: set = set()
        start_index = 0

        while True:
            url = (f"https://www.{marketplace}/gp/your-account/order-history"
                   f"?orderFilter=year-{year}&startIndex={start_index}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # Pull both raw HTML (for order IDs) and visible text (for dates)
            html = await page.content()
            page_text = await page.evaluate("() => document.body.innerText")

            # Find every order ID on this page (pattern: 3-7-7 digits)
            found_ids = list(dict.fromkeys(re.findall(r'\b(\d{3}-\d{7}-\d{7})\b', html)))
            new_ids = [oid for oid in found_ids if oid not in seen_ids]

            if not new_ids:
                break  # no new orders → stop pagination

            for order_id in new_ids:
                seen_ids.add(order_id)
                order_date = self._find_order_date(page_text, order_id, year)
                if not order_date or not (start_date <= order_date <= end_date):
                    continue
                amount = self._find_order_amount(page_text, order_id)
                items  = self._find_order_items(html, order_id)
                orders.append({
                    "id":       order_id,
                    "date":     order_date.isoformat(),
                    "total":    amount,
                    "items":    items,
                    "category": self._categorize(items),
                })

            await send({"type": "status",
                        "message": f"Page {start_index // 10 + 1} — {len(new_ids)} commande(s) détectée(s)"})

            # Next page button
            next_btn = page.locator(
                '.a-pagination .a-last:not(.a-disabled) a, '
                'li.a-last:not(.a-disabled) a'
            )
            if await next_btn.count() > 0:
                start_index += 10
                await asyncio.sleep(1)
            else:
                break

        return orders

    def _find_order_date(self, page_text: str, order_id: str, year: int):
        """Find the date of an order by looking at text surrounding its ID."""
        idx = page_text.find(order_id)
        # Search within ±800 chars around the order ID
        context = page_text[max(0, idx - 800): idx + 800] if idx != -1 else page_text

        # French date: "5 janvier 2024"
        for month_name, month_num in MONTH_MAP_FR.items():
            m = re.search(
                rf'(\d{{1,2}})\s+{month_name}\s+(\d{{4}})', context, re.IGNORECASE)
            if m:
                try:
                    return date(int(m.group(2)), month_num, int(m.group(1)))
                except ValueError:
                    pass

        # English date: "January 5, 2024" or "5 January 2024"
        for month_name, month_num in MONTH_MAP_EN.items():
            for pat in [
                rf'(\d{{1,2}})\s+{month_name}[\s,]+(\d{{4}})',
                rf'{month_name}\s+(\d{{1,2}})[\s,]+(\d{{4}})',
            ]:
                m = re.search(pat, context, re.IGNORECASE)
                if m:
                    try:
                        day = int(m.group(1))
                        yr = int(m.group(2))
                        return date(yr, month_num, day)
                    except ValueError:
                        pass

        # Fallback: mid-year (order is on the correct year page, so include it)
        return date(year, 6, 15)

    def _find_order_amount(self, page_text: str, order_id: str) -> float:
        idx = page_text.find(order_id)
        # Look in the 1 200 chars after the order ID (where the total is shown)
        ctx = page_text[idx: idx + 1200] if idx != -1 else ""

        # Prefer a labelled total
        m = re.search(
            r'(?:Total(?:\s+de\s+la\s+commande)?|Order\s+[Tt]otal|Montant\s+total)'
            r'[\s:]*(\d[\d\s]*[,\.]\d{2})\s*€',
            ctx, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(' ', '').replace(',', '.'))

        # Fallback: largest € amount in context (usually the order total)
        amounts = [float(a.replace(' ', '').replace(',', '.'))
                   for a in re.findall(r'(\d[\d\s]*[,\.]\d{2})\s*€', ctx)]
        return max(amounts) if amounts else 0.0

    def _find_order_items(self, html: str, order_id: str) -> list[str]:
        idx = html.find(order_id)
        # Product links always contain /dp/<ASIN>
        ctx = html[max(0, idx - 200): idx + 4000] if idx != -1 else ""
        titles = re.findall(
            r'<a[^>]+href="[^"]*\/dp\/[A-Z0-9]{10}[^"]*"[^>]*>\s*([^<]{5,150})\s*<\/a>',
            ctx)
        skip = {'voir', 'détail', 'retour', 'aide', 'connexion', 'compte',
                'commande', 'panier', 'liste', 'partager', 'signaler'}
        items = [t.strip() for t in titles
                 if t.strip() and not any(s in t.lower() for s in skip)]
        return list(dict.fromkeys(items))[:6]  # dedupe, max 6

    def _categorize(self, items: list[str]) -> str:
        from analyzer import categorize_item
        if not items:
            return "Autres"
        scores: dict = {}
        for item in items:
            cat = categorize_item(item)
            scores[cat] = scores.get(cat, 0) + 1
        return max(scores, key=scores.get)
