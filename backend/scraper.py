import asyncio
import json
import os
import re
from datetime import datetime, date
from pathlib import Path
from playwright.async_api import async_playwright

def _strip_html(raw: str) -> str:
    """Strip HTML tags, decode entities, collapse whitespace."""
    text = re.sub(r'<[^>]+>', ' ', raw)
    for ent, ch in [('&amp;', '&'), ('&quot;', '"'), ('&#39;', "'"),
                    ('&lt;', '<'), ('&gt;', '>'), ('&nbsp;', ' ')]:
        text = text.replace(ent, ch)
    return ' '.join(text.split())


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

    async def _apply_year_filter(self, page, marketplace: str, year: int):
        """Ensure the order-history page is filtered to the requested year.
        Amazon defaults to 'last 3 months'; we need to force the year view."""
        # Navigate with the year filter in the URL (works in most cases)
        url = (f"https://www.{marketplace}/gp/your-account/order-history"
               f"?orderFilter=year-{year}&startIndex=0")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)

        # Verify the filter took effect: check that a <select> or link shows the year,
        # or that the page doesn't still say "3 derniers mois" / "last 3 months".
        page_text = await page.evaluate("() => document.body.innerText")
        still_default = any(k in page_text.lower() for k in [
            'derniers mois', 'last 3 months', '3 months',
        ])

        if still_default:
            # Try clicking the filter dropdown and selecting the year
            try:
                select = page.locator('select[name="orderFilter"], #time-filter')
                if await select.count() > 0:
                    await select.select_option(value=f'year-{year}')
                    await asyncio.sleep(2)
                else:
                    # Try clicking a link/button for the year
                    year_link = page.locator(
                        f'a:has-text("{year}"), button:has-text("{year}")'
                    ).first
                    if await year_link.count() > 0:
                        await year_link.click()
                        await asyncio.sleep(2)
            except Exception:
                pass  # URL approach remains; proceed anyway

    async def _get_year_orders(self, page, marketplace, year,
                                start_date, end_date, send):
        """Extract orders by scanning raw HTML for order-ID patterns.
        This avoids relying on Amazon's frequently-changing CSS classes."""
        orders = []
        seen_ids: set = set()
        cancelled_count = 0
        start_index = 0

        # Force the correct year filter (Amazon defaults to "last 3 months")
        await self._apply_year_filter(page, marketplace, year)

        while True:
            if start_index > 0:
                url = (f"https://www.{marketplace}/gp/your-account/order-history"
                       f"?orderFilter=year-{year}&startIndex={start_index}")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)

            html      = await page.content()
            page_text = await page.evaluate("() => document.body.innerText")

            found_ids = list(dict.fromkeys(re.findall(r'\b(\d{3}-\d{7}-\d{7})\b', html)))
            new_ids   = [oid for oid in found_ids if oid not in seen_ids]

            if not new_ids:
                break

            for order_id in new_ids:
                seen_ids.add(order_id)

                # ── Skip cancelled orders ──────────────────────────────────
                if self._is_cancelled(page_text, order_id):
                    cancelled_count += 1
                    await send({"type": "warning",
                                "message": f"Commande {order_id} annulée — ignorée"})
                    continue

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

            await send({
                "type":      "status",
                "message":   (
                    f"Page {start_index // 10 + 1} — "
                    f"{len(orders)} retenue(s)"
                    + (f", {cancelled_count} annulée(s) ignorée(s)" if cancelled_count else "")
                ),
            })

            next_btn = page.locator(
                '.a-pagination .a-last:not(.a-disabled) a, '
                'li.a-last:not(.a-disabled) a'
            )
            if await next_btn.count() > 0:
                start_index += 10
                await asyncio.sleep(1)
            else:
                break

        if cancelled_count:
            await send({"type": "info",
                        "message": f"⚠️ {cancelled_count} commande(s) annulée(s) exclue(s) du bilan."})
        return orders

    # Keywords that indicate a cancelled order (checked in the text that follows
    # the order ID on the history page)
    _CANCEL_KEYWORDS = [
        'annulée', 'annulé', 'annulation',
        'commande annulée', 'commande annulé',
        'cancelled', 'canceled', 'order cancelled', 'order canceled',
    ]

    def _is_cancelled(self, page_text: str, order_id: str) -> bool:
        """Return True if the order appears to be cancelled."""
        idx = page_text.find(order_id)
        if idx == -1:
            return False
        # Status text is shown right after the order ID block (~600 chars)
        ctx = page_text[idx: idx + 600].lower()
        return any(kw in ctx for kw in self._CANCEL_KEYWORDS)

    def _find_order_date(self, page_text: str, order_id: str, year: int):
        """Find the ORDER placement date (not shipping/delivery date).

        Priority:
        1. Labelled placement date: "Commande passée le …" / "Order placed …"
        2. First valid date found in the text block before the order ID
        3. Fallback: mid-year (still on the correct year page)
        """
        idx = page_text.find(order_id)
        # The order-date label appears BEFORE the order ID in the card
        before = page_text[max(0, idx - 600): idx] if idx != -1 else ""
        after  = page_text[idx: idx + 200]           if idx != -1 else ""
        combined = before + after

        def _try_fr(text: str):
            for month_name, month_num in MONTH_MAP_FR.items():
                m = re.search(
                    rf'(\d{{1,2}})\s+{month_name}\s+(\d{{4}})', text, re.IGNORECASE)
                if m:
                    try:
                        return date(int(m.group(2)), month_num, int(m.group(1)))
                    except ValueError:
                        pass
            return None

        def _try_en(text: str):
            for month_name, month_num in MONTH_MAP_EN.items():
                for pat in [
                    rf'(\d{{1,2}})\s+{month_name}[\s,]+(\d{{4}})',
                    rf'{month_name}\s+(\d{{1,2}})[\s,]+(\d{{4}})',
                ]:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        try:
                            return date(int(m.group(2)), month_num, int(m.group(1)))
                        except ValueError:
                            pass
            return None

        # ── Pass 1: look for an explicit order-date label ──────────────────
        for label_pat in [
            r'(?:Commande\s+pass[ée]e?\s+le|pass[ée]e?\s+le)\s+(.{5,30})',
            r'(?:Order\s+placed|Ordered\s+on|Date\s+de\s+commande)\s*:?\s*(.{5,30})',
        ]:
            m = re.search(label_pat, combined, re.IGNORECASE)
            if m:
                snippet = m.group(1)
                d = _try_fr(snippet) or _try_en(snippet)
                if d:
                    return d

        # ── Pass 2: first date that appears BEFORE the order ID ────────────
        d = _try_fr(before) or _try_en(before)
        if d:
            return d

        # ── Pass 3: any date anywhere around the order ─────────────────────
        d = _try_fr(combined) or _try_en(combined)
        if d:
            return d

        # ── Fallback ───────────────────────────────────────────────────────
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
        ctx = html[max(0, idx - 500): idx + 6000] if idx != -1 else ""

        titles: list[str] = []

        # Strategy 1 – product links /dp/<ASIN> (inner HTML may have nested tags)
        for m in re.finditer(
            r'<a\b[^>]*href="[^"]*\/dp\/([A-Z0-9]{10})[^"]*"[^>]*>(.*?)<\/a>',
            ctx, re.DOTALL | re.IGNORECASE
        ):
            clean = _strip_html(m.group(2))
            if 8 <= len(clean) <= 250:
                titles.append(clean)

        # Strategy 2 – fallback: <a class="a-link-normal"> with substantive text
        if not titles:
            for m in re.finditer(
                r'<a\b[^>]*class="[^"]*a-link-normal[^"]*"[^>]*>(.*?)<\/a>',
                ctx, re.DOTALL | re.IGNORECASE
            ):
                clean = _strip_html(m.group(1))
                if 12 <= len(clean) <= 250:
                    titles.append(clean)

        SKIP = {'voir', 'détail', 'retour', 'aide', 'connexion', 'compte',
                'commande', 'panier', 'liste', 'partager', 'signaler',
                'ajouter', 'acheter', 'suivre', 'télécharger', 'imprimer',
                'toutes nos', 'continuer', 'filtrer'}
        seen: set = set()
        items: list[str] = []
        for t in titles:
            if t in seen:
                continue
            if any(s in t.lower() for s in SKIP):
                continue
            seen.add(t)
            items.append(t)
        return items[:6]

    def _categorize(self, items: list[str]) -> str:
        from analyzer import categorize_item
        if not items:
            return "Autres"
        scores: dict = {}
        for item in items:
            cat = categorize_item(item)
            scores[cat] = scores.get(cat, 0) + 1
        return max(scores, key=scores.get)
