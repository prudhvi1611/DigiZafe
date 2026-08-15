"""
Playwright Green broker runner (AIDR watcher/brokers lineage — Python re-impl).

Rules:
- Only Green brokers
- dry_run fills but does not submit
- CAPTCHA → return captcha_needed (never require CapSolver)
- Timeouts hard-enforced
- No cross-user browser context reuse
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.remediation_profile import RemediationProfile
from app.domain.remediation_states import BrokerOptOutStatus

logger = get_logger(__name__)


@dataclass
class RunnerResult:
    status: str  # BrokerOptOutStatus value
    detail: str = ""
    open_url: str | None = None
    captcha_type: str | None = None
    sitekey: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "detail": self.detail,
            "open_url": self.open_url,
            "captcha_type": self.captcha_type,
            "sitekey": self.sitekey,
            "meta": self.meta,
        }


class PlaywrightBrokerRunner:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def run_broker(
        self,
        broker: dict[str, Any],
        profile: RemediationProfile,
        *,
        dry_run: bool = False,
        captcha_token: str | None = None,
        user_scope: str = "anon",
    ) -> RunnerResult:
        method = (broker.get("method") or "direct_form").lower()
        if method == "manual":
            return RunnerResult(
                status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                detail="Broker requires manual / open-in-browser path (free CAPTCHA path)",
                open_url=broker.get("opt_out_url"),
                meta={"aidr_lineage": "manual"},
            )

        if broker.get("requires_captcha") and not captcha_token:
            mode = (self.settings.captcha_mode or "manual").lower()
            if mode in {"manual", "open_in_browser"} or not self.settings.feature_capsolver:
                return RunnerResult(
                    status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    detail="CAPTCHA required — free path: solve manually or open_in_browser",
                    open_url=broker.get("opt_out_url"),
                    captcha_type="recaptcha_or_unknown",
                    meta={"captcha_mode": mode},
                )
            # CapSolver optional path (feature flag)
            token = await self._try_capsolver(broker)
            if not token:
                return RunnerResult(
                    status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                    detail="CapSolver unavailable or failed — falling back to manual",
                    open_url=broker.get("opt_out_url"),
                )
            captcha_token = token

        try:
            return await self._playwright_direct_form(
                broker, profile, dry_run=dry_run, captcha_token=captcha_token, user_scope=user_scope
            )
        except Exception as e:
            logger.exception("playwright_broker_failed", broker=broker.get("id"), error=str(e))
            msg = str(e).lower()
            if "err_name_not_resolved" in msg or "net::" in msg:
                return RunnerResult(status=BrokerOptOutStatus.DEAD.value, detail=str(e)[:500])
            return RunnerResult(status=BrokerOptOutStatus.ERROR.value, detail=str(e)[:500])

    async def _try_capsolver(self, broker: dict[str, Any]) -> str | None:
        if not self.settings.feature_capsolver or not self.settings.capsolver_api_key:
            return None
        # Optional paid path — stub that does not hard-depend
        logger.info("capsolver_skipped_or_unimplemented", broker=broker.get("id"))
        return None

    async def _playwright_direct_form(
        self,
        broker: dict[str, Any],
        profile: RemediationProfile,
        *,
        dry_run: bool,
        captcha_token: str | None,
        user_scope: str,
    ) -> RunnerResult:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return RunnerResult(
                status=BrokerOptOutStatus.ERROR.value,
                detail="playwright not installed in this worker image",
            )

        url = broker.get("opt_out_url")
        if not url or not str(url).startswith("https://"):
            return RunnerResult(status=BrokerOptOutStatus.DEAD.value, detail="Invalid opt_out_url")

        timeout_ms = int(self.settings.broker_runner_timeout_seconds * 1000)
        field_map = broker.get("form_field_map") or {}
        submit_sel = broker.get("submit_selector")
        success_hints = [h.lower() for h in (broker.get("success_hints") or [])]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.settings.playwright_headless)
            context = await browser.new_context(
                user_agent="DigiZafe-Remediation/0.7 (personal self-only opt-out; +local)",
                locale="en-US",
            )
            page = await context.new_page()
            page.set_default_timeout(timeout_ms)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if resp and resp.status == 404:
                    return RunnerResult(status=BrokerOptOutStatus.DEAD.value, detail="404")

                # Detect obvious captcha widgets
                content = (await page.content()).lower()
                if "recaptcha" in content or "hcaptcha" in content or "cf-turnstile" in content:
                    if not captcha_token:
                        sitekey = None
                        m = re.search(r'data-sitekey=["\']([^"\']+)', content)
                        if m:
                            sitekey = m.group(1)
                        return RunnerResult(
                            status=BrokerOptOutStatus.CAPTCHA_NEEDED.value,
                            detail="CAPTCHA widget detected on page",
                            open_url=url,
                            captcha_type="detected",
                            sitekey=sitekey,
                        )

                # Fill fields
                value_for = {
                    "email": profile.email or "",
                    "first_name": profile.first_name or "",
                    "last_name": profile.last_name or "",
                    "name": profile.full_name or f"{profile.first_name or ''} {profile.last_name or ''}".strip(),
                    "phone": profile.phone or "",
                    "state": profile.state or "",
                    "city": profile.city or "",
                    "zip": profile.zip or "",
                }
                filled = 0
                for logical, selector in field_map.items():
                    val = value_for.get(logical, "")
                    if not val or not selector:
                        continue
                    try:
                        loc = page.locator(selector).first
                        if await loc.count() == 0:
                            continue
                        tag = await loc.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            await loc.select_option(label=val)
                        else:
                            await loc.fill(val)
                        filled += 1
                    except Exception as fe:
                        logger.info("field_fill_skip", field=logical, error=str(fe))

                if captcha_token:
                    # Best-effort inject token into common textarea
                    try:
                        await page.evaluate(
                            """(token) => {
                              const el = document.querySelector('[name="g-recaptcha-response"], #g-recaptcha-response');
                              if (el) { el.value = token; }
                            }""",
                            captcha_token,
                        )
                    except Exception:
                        pass

                if dry_run:
                    return RunnerResult(
                        status=BrokerOptOutStatus.SUBMITTED.value,
                        detail=f"dry_run: filled {filled} fields, submit skipped",
                        meta={"dry_run": True, "filled": filled, "url": url},
                    )

                if submit_sel:
                    try:
                        await page.locator(submit_sel).first.click(timeout=5000)
                        await page.wait_for_timeout(1500)
                    except Exception as se:
                        return RunnerResult(
                            status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                            detail=f"Submit failed: {se}",
                            open_url=url,
                        )
                else:
                    return RunnerResult(
                        status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                        detail="No submit selector",
                        open_url=url,
                    )

                body = (await page.content()).lower()
                if any(h in body for h in success_hints):
                    return RunnerResult(
                        status=BrokerOptOutStatus.SUBMITTED.value,
                        detail="Form submitted; success hints matched",
                        meta={"filled": filled, "url": url},
                    )
                # Heuristic accept
                if filled > 0:
                    return RunnerResult(
                        status=BrokerOptOutStatus.SUBMITTED.value,
                        detail="Form submitted (heuristic — verify separately)",
                        meta={"filled": filled, "url": url, "confidence": "low"},
                    )
                return RunnerResult(
                    status=BrokerOptOutStatus.MANUAL_NEEDED.value,
                    detail="Could not fill/submit confidently",
                    open_url=url,
                )
            finally:
                await context.close()
                await browser.close()

    async def verify_not_listed(
        self,
        broker: dict[str, Any],
        profile: RemediationProfile,
        *,
        user_scope: str = "anon",
    ) -> RunnerResult:
        """
        Best-effort re-check (AIDR verify lineage).
        Without a reliable public search API per broker, open opt-out/search page
        and look for name/email absence — honest low confidence.
        """
        search_tpl = broker.get("search_url_template")
        url = search_tpl.format(
            name=(profile.full_name or "").replace(" ", "+"),
            state=profile.state or "",
        ) if search_tpl else broker.get("opt_out_url")
        if not url:
            return RunnerResult(
                status=BrokerOptOutStatus.STILL_LISTED.value,
                detail="No verify URL — cannot confirm",
                meta={"confidence": "none"},
            )
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return RunnerResult(status=BrokerOptOutStatus.ERROR.value, detail="playwright missing")

        needle = (profile.email or profile.full_name or "").lower()
        if not needle:
            return RunnerResult(
                status=BrokerOptOutStatus.NOT_LISTED.value,
                detail="No needle to search — treating as N/A",
                meta={"confidence": "none"},
            )

        timeout_ms = int(self.settings.broker_runner_timeout_seconds * 1000)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                body = (await page.content()).lower()
                if needle in body:
                    return RunnerResult(
                        status=BrokerOptOutStatus.STILL_LISTED.value,
                        detail="Needle still present on page (low-confidence verify)",
                        open_url=url,
                        meta={"confidence": "low"},
                    )
                return RunnerResult(
                    status=BrokerOptOutStatus.VERIFIED_REMOVED.value,
                    detail="Needle not found on page (low-confidence verify)",
                    open_url=url,
                    meta={"confidence": "low"},
                )
            except Exception as e:
                return RunnerResult(status=BrokerOptOutStatus.ERROR.value, detail=str(e)[:500])
            finally:
                await browser.close()
